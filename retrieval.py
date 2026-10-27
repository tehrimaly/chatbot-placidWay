"""
BM25-based Retrieval Engine for PlacidWay Knowledge Base.

Loads chunked documents from data/knowledge.json, indexes using rank_bm25.BM25Okapi,
provides top-k query matching with score thresholding, and supports live reloading
via reload_index().
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rank_bm25 import BM25Okapi

logger = logging.getLogger("retrieval")

DATA_DIR = Path(__file__).resolve().parent / "data"
KNOWLEDGE_FILE = DATA_DIR / "knowledge.json"

# Score threshold for BM25: if best score is below this, query is considered out-of-corpus
DEFAULT_SCORE_THRESHOLD = 1.0


STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "at", "by", "from",
    "with", "about", "as", "into", "like", "through", "after", "over", "between",
    "out", "against", "during", "without", "before", "under", "around", "among",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "can", "could", "will", "would", "shall", "should",
    "may", "might", "must", "it", "its", "this", "that", "these", "those",
    "i", "you", "he", "she", "we", "they", "me", "him", "her", "us", "them",
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how"
}


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric and currency words."""
    if not text:
        return []
    return re.findall(r"\b[a-zA-Z0-9_\$]+\b", text.lower())


def tokenize_query(query: str) -> List[str]:
    """Tokenize query and strip common stopwords so BM25 focuses on substantive terms."""
    all_tokens = tokenize(query)
    content_tokens = [t for t in all_tokens if t not in STOPWORDS]
    # If query was entirely stopwords (e.g. 'how are you'), fall back to all tokens
    return content_tokens if content_tokens else all_tokens


class BM25Retriever:
    """Manages the in-memory BM25 index over PlacidWay knowledge chunks."""

    def __init__(self, knowledge_path: Path = KNOWLEDGE_FILE):
        self.knowledge_path = knowledge_path
        self.chunks: List[Dict[str, Any]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.corpus_tokens: List[List[str]] = []
        self.load_index()

    def load_index(self) -> int:
        """Loads chunks from JSON and builds the BM25 index."""
        if not self.knowledge_path.exists():
            logger.warning("Knowledge file %s does not exist yet.", self.knowledge_path)
            self.chunks = []
            self.bm25 = None
            self.corpus_tokens = []
            return 0

        with open(self.knowledge_path, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)

        self.corpus_tokens = [
            tokenize(
                f"{chunk.get('page_title', '')} "
                f"{chunk.get('section_heading', '')} "
                f"{chunk.get('text', '')}"
            )
            for chunk in self.chunks
        ]

        if self.corpus_tokens:
            self.bm25 = BM25Okapi(self.corpus_tokens)
            logger.info("Indexed %d chunks with BM25Okapi.", len(self.chunks))
        else:
            self.bm25 = None
            logger.warning("Corpus tokens empty; BM25 index not built.")

        return len(self.chunks)

    def reload(self) -> int:
        """Reload the knowledge base and rebuild the BM25 index without restart."""
        count = self.load_index()
        logger.info("BM25 index reloaded with %d chunks.", count)
        return count

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = DEFAULT_SCORE_THRESHOLD,
    ) -> Tuple[List[Dict[str, Any]], float, bool]:
        """
        Retrieves top-k relevant chunks for the given query.

        Returns:
            Tuple of:
            - List of retrieved chunk dictionaries (augmented with BM25 score)
            - Best BM25 score
            - Boolean flag indicating if relevant content was found (score >= threshold)
        """
        if not self.bm25 or not self.chunks:
            return [], 0.0, False

        query_tokens = tokenize_query(query)
        if not query_tokens:
            return [], 0.0, False

        scores = self.bm25.get_scores(query_tokens)
        if len(scores) == 0:
            return [], 0.0, False

        # Sort indices by score descending
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        top_indices = ranked_indices[:top_k]

        best_score = float(scores[top_indices[0]]) if top_indices else 0.0

        if best_score < threshold:
            logger.info("Query '%s' top score %.2f is below threshold %.2f (not in content)", query, best_score, threshold)
            return [], best_score, False

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            # Only include chunks with positive score
            if score > 0:
                chunk_copy = dict(self.chunks[idx])
                chunk_copy["score"] = round(score, 3)
                results.append(chunk_copy)

        return results, best_score, True


# Global singleton instance
retriever = BM25Retriever()


def get_retriever() -> BM25Retriever:
    """Returns the global retriever instance."""
    return retriever


def reload_index() -> int:
    """Reloads the global retriever index."""
    return retriever.reload()
