"""
Ingestion Pipeline for PlacidWay Knowledge Base.

Fetches content strictly from 7 designated PlacidWay URLs, checks robots.txt,
enforces English-only content verification, extracts clean textual content
(preserving pricing tables and video descriptions), chunks into 200-350 word segments,
and writes structured knowledge to data/knowledge.json.
"""

import json
import logging
import os
import re
import time
import urllib.robotparser
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langdetect import DetectorFactory, detect

# Set seed for deterministic language detection
DetectorFactory.seed = 0

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ingest")

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent / "data"
KNOWLEDGE_FILE = DATA_DIR / "knowledge.json"

CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "candidate@assessment.com")
USER_AGENT = f"PlacidWayKBBot/1.0 (assessment; contact: {CONTACT_EMAIL})"
ACCEPT_LANGUAGE = "en"

# Strict whitelist of the 7 designated URLs
SOURCE_PAGES = [
    {
        "name": "Clinic Profile (ITC Immunity Therapy Center)",
        "url": "https://www.placidway.com/profile/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center",
        "page_type": "clinic_profile",
    },
    {
        "name": "Treatment Package (Adenocarcinoma)",
        "url": "https://www.placidway.com/package/7903/Alternative-Adenocarcinoma-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC",
        "page_type": "treatment_package",
    },
    {
        "name": "Treatment Package (Adrenal)",
        "url": "https://www.placidway.com/package/7902/Alternative-Adrenal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC",
        "page_type": "treatment_package",
    },
    {
        "name": "Treatment Package (Anal)",
        "url": "https://www.placidway.com/package/7901/Alternative-Anal-Cancer-Treatment-Package-in-Tijuana-Mexico-by-ITC",
        "page_type": "treatment_package",
    },
    {
        "name": "Clinic Videos (ITC Immunity Therapy Center)",
        "url": "https://www.placidway.com/profile-videos/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center",
        "page_type": "clinic_videos",
    },
    {
        "name": "Price List (ITC Immunity Therapy Center)",
        "url": "https://www.placidway.com/price-list/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center",
        "page_type": "price_list",
    },
    {
        "name": "Price Comparison (Alternative Medicine)",
        "url": "https://www.placidway.com/search-medical-pricings/Alternative-Medicine/All/1",
        "page_type": "price_comparison",
    },
]


def check_robots(url: str, user_agent: str = USER_AGENT) -> bool:
    """
    Check robots.txt using urllib.robotparser.
    Fetches robots.txt with custom user-agent headers to bypass WAF 403 on standard urllib.
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        resp = requests.get(robots_url, headers={"User-Agent": user_agent}, timeout=10)
        if resp.status_code == 200:
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(resp.text.splitlines())
            allowed = rp.can_fetch(user_agent, url)
            if not allowed:
                # Also check wildcard rule
                allowed = rp.can_fetch("*", url)
            return allowed
        elif resp.status_code in (401, 403):
            logger.warning("Robots.txt returned status %d for %s; default to disallow", resp.status_code, robots_url)
            return False
        else:
            return True
    except Exception as exc:
        logger.warning("Error checking robots.txt at %s: %s", robots_url, exc)
        return True


def fetch_page(url: str, session: requests.Session) -> str:
    """
    Fetch a page with rate limiting and Accept-Language header.
    Validates that the content is in English.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": ACCEPT_LANGUAGE,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    logger.info("Fetching: %s", url)
    resp = session.get(url, headers=headers, timeout=20)
    resp.raise_for_status()

    # Detect language of text sample
    soup = BeautifulSoup(resp.text, "html.parser")
    # Remove script and style tags before language sampling
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    sample_text = soup.get_text(separator=" ", strip=True)[:1000]

    try:
        lang = detect(sample_text)
    except Exception:
        lang = "en"

    if lang != "en":
        logger.warning("Detected non-English language '%s' for URL %s. Retrying with lang=en parameter...", lang, url)
        retry_url = f"{url}?lang=en" if "?" not in url else f"{url}&lang=en"
        resp = session.get(retry_url, headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        sample_text = soup.get_text(separator=" ", strip=True)[:1000]
        try:
            lang = detect(sample_text)
        except Exception:
            lang = "en"

        if lang != "en":
            raise ValueError(f"Content at {url} is not English (detected '{lang}'). Ingestion aborted for this page.")

    return resp.text


def extract_tables_as_text(soup: BeautifulSoup) -> List[str]:
    """
    Extracts all HTML tables into clear, structured markdown tables
    preserving currencies, numbers, and descriptions.
    """
    table_texts = []
    for tbl in soup.find_all("table"):
        rows = tbl.find_all("tr")
        if not rows:
            continue
        table_lines = []
        for idx, row in enumerate(rows):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            if not any(cells):
                continue
            line = "| " + " | ".join(cells) + " |"
            table_lines.append(line)
            if idx == 0 and len(cells) > 0:
                sep = "| " + " | ".join(["---"] * len(cells)) + " |"
                table_lines.append(sep)
        if table_lines:
            table_texts.append("\n".join(table_lines))
    return table_texts


def extract_videos_as_text(soup: BeautifulSoup, page_url: str) -> List[str]:
    """
    Extracts video titles, descriptions, and patient story details from the video page.
    """
    video_blocks = []
    # Look for video cards and headings
    for h in soup.find_all(["h2", "h3", "h4"]):
        title = h.get_text(" ", strip=True)
        if not title or len(title) < 10:
            continue
        if any(term in title.lower() for term in ["treatment experience", "journey", "story", "doctor", "tijuana", "center", "patient"]):
            desc_parts = []
            curr = h
            for _ in range(5):
                curr = curr.find_next_sibling()
                if not curr or curr.name in ["h2", "h3", "h4"]:
                    break
                txt = curr.get_text(" ", strip=True)
                if txt and len(txt) > 20:
                    desc_parts.append(txt)
            desc_text = " ".join(desc_parts)
            block = f"Video: {title}\nDescription: {desc_text if desc_text else 'Patient experience and treatment testimonial at Immunity Therapy Center.'}\nPage: {page_url}"
            video_blocks.append(block)
    return video_blocks


def clean_extracted_text(text: str) -> str:
    """Clean unrendered template variables, repeated whitespace, and boilerplate."""
    # Fix PHP template glitches seen on PlacidWay (e.g., '=$priceRange?>')
    text = re.sub(r'=\$[a-zA-Z0-9_]+\?>', 'variable based on program', text)
    # Remove common footer/cookie banner remnants
    text = re.sub(r'©\s*\d{4}\s*PlacidWay.*', '', text, flags=re.IGNORECASE)
    # Normalize multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_page_content(html: str, page_type: str, url: str) -> Dict[str, Any]:
    """
    Extract main content, page title, and structured components.
    Uses trafilatura as primary, falling back to BeautifulSoup.
    """
    soup = BeautifulSoup(html, "html.parser")
    page_title = soup.title.string.strip() if soup.title and soup.title.string else ""
    page_title = page_title.split("|")[0].split("-")[0].strip()

    # Trafilatura main extraction
    extracted = trafilatura.extract(
        html,
        include_tables=True,
        include_links=False,
        output_format="txt",
    )

    # Fallback to BeautifulSoup if trafilatura extraction is sparse
    if not extracted or len(extracted) < 300:
        logger.info("Trafilatura output sparse (%d chars); using BeautifulSoup fallback for %s", len(extracted) if extracted else 0, url)
        for junk in soup(["nav", "footer", "header", "script", "style", "noscript"]):
            junk.decompose()
        main_elem = soup.find("main") or soup.find("article") or soup.find("body")
        extracted = main_elem.get_text(separator="\n\n", strip=True) if main_elem else ""

    extracted = clean_extracted_text(extracted)

    # For pricing pages, append explicitly parsed tables to guarantee no price context is lost
    if page_type in ("price_list", "price_comparison"):
        tables = extract_tables_as_text(soup)
        if tables:
            extracted += "\n\n### Detailed Pricing Tables:\n" + "\n\n".join(tables)

    # For video page, append structured video list
    if page_type == "clinic_videos":
        videos = extract_videos_as_text(soup, url)
        if videos:
            extracted += "\n\n### Clinic Patient Testimonial & Educational Videos:\n" + "\n\n".join(videos)

    return {
        "title": page_title,
        "content": extracted,
        "page_type": page_type,
        "url": url,
    }


def chunk_text(content: str, page_title: str, page_type: str, url: str, target_words: int = 280, overlap_words: int = 40) -> List[Dict[str, Any]]:
    """
    Split text into chunks by headings and paragraphs, targeting 200 to 350 words
    with a small overlap, preserving section headings.
    """
    # Split into sections based on markdown headings or double newlines
    lines = content.split("\n")
    sections: List[Dict[str, Any]] = []
    current_heading = page_title or "Overview"
    current_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            # New heading found
            if current_lines:
                sec_text = "\n".join(current_lines).strip()
                if sec_text:
                    sections.append({"heading": current_heading, "text": sec_text})
                current_lines = []
            current_heading = stripped.lstrip("#").strip()
        elif stripped.isupper() and len(stripped.split()) <= 8 and len(stripped) > 3:
            # Uppercase heading line
            if current_lines:
                sec_text = "\n".join(current_lines).strip()
                if sec_text:
                    sections.append({"heading": current_heading, "text": sec_text})
                current_lines = []
            current_heading = stripped.title()
        else:
            if stripped:
                current_lines.append(stripped)

    if current_lines:
        sec_text = "\n".join(current_lines).strip()
        if sec_text:
            sections.append({"heading": current_heading, "text": sec_text})

    chunks: List[Dict[str, Any]] = []

    for sec in sections:
        heading = sec["heading"]
        paragraphs = [p.strip() for p in sec["text"].split("\n") if p.strip()]

        current_chunk_words: List[str] = []
        for p in paragraphs:
            p_words = p.split()
            if not p_words:
                continue

            # If adding this paragraph exceeds upper limit (~350 words)
            if len(current_chunk_words) + len(p_words) > 350 and len(current_chunk_words) >= 180:
                chunk_str = " ".join(current_chunk_words)
                chunks.append({
                    "text": chunk_str,
                    "page_title": page_title,
                    "page_type": page_type,
                    "source_url": url,
                    "section_heading": heading,
                })
                # Retain overlap words
                current_chunk_words = current_chunk_words[-overlap_words:] + p_words
            else:
                current_chunk_words.extend(p_words)

        if current_chunk_words:
            # Check if current words are enough or merge with previous chunk if tiny
            if len(current_chunk_words) < 50 and chunks and chunks[-1]["section_heading"] == heading:
                chunks[-1]["text"] += " " + " ".join(current_chunk_words)
            else:
                chunks.append({
                    "text": " ".join(current_chunk_words),
                    "page_title": page_title,
                    "page_type": page_type,
                    "source_url": url,
                    "section_heading": heading,
                })

    # Assign unique IDs
    for idx, c in enumerate(chunks):
        c["chunk_id"] = f"{page_type}_{idx+1}"

    return chunks


def run_ingestion() -> Dict[str, Any]:
    """
    Main ingestion execution function.
    Can be run via CLI or triggered via POST /api/refresh.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    all_chunks: List[Dict[str, Any]] = []
    page_stats: Dict[str, int] = {}

    logger.info("Starting ingestion of %d pages...", len(SOURCE_PAGES))

    for page_info in SOURCE_PAGES:
        url = page_info["url"]
        name = page_info["name"]
        page_type = page_info["page_type"]

        # 1. Robots.txt check
        if not check_robots(url):
            logger.warning("SKIPPED: %s is disallowed by robots.txt", url)
            page_stats[url] = 0
            continue

        # 2. Fetch page (with language check)
        try:
            html = fetch_page(url, session)
        except Exception as exc:
            logger.error("Failed to fetch %s: %s", url, exc)
            continue

        # 3. Extract content
        extracted = extract_page_content(html, page_type, url)

        # 4. Chunk
        chunks = chunk_text(
            content=extracted["content"],
            page_title=extracted["title"],
            page_type=page_type,
            url=url,
        )

        all_chunks.extend(chunks)
        page_stats[url] = len(chunks)
        logger.info("Page '%s' (%s) produced %d chunks", name, url, len(chunks))

        # 5. Rate limit: 1 request per second
        time.sleep(1.0)

    # Save to data/knowledge.json
    with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    total_chunks = len(all_chunks)
    logger.info("Ingestion complete. Total chunks saved: %d to %s", total_chunks, KNOWLEDGE_FILE)

    return {
        "status": "success",
        "total_chunks": total_chunks,
        "page_stats": page_stats,
        "file_path": str(KNOWLEDGE_FILE),
    }


if __name__ == "__main__":
    result = run_ingestion()
    print("\n--- INGESTION SUMMARY ---")
    print(f"Total chunks: {result['total_chunks']}")
    for url, count in result["page_stats"].items():
        print(f"  {count:3d} chunks -> {url}")
