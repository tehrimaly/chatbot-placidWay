"""
FastAPI Application for PlacidWay Medical Tourism Knowledge Chatbot.

Serves:
- GET /: Chatbot frontend UI
- POST /api/chat: Chat processing with rewrite, BM25 retrieval, and Gemini answer generation
- GET /api/health: Service health and knowledge base status
- POST /api/refresh: Protected endpoint to re-run ingestion and reload the index
- POST /api/lead: Captures optional leads into data/leads.jsonl
- GET /admin: Protected admin UI listing unanswered questions
- GET /api/admin/unanswered: Protected JSON API for unanswered questions
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ingest import run_ingestion
from llm import generate_chat_response
from retrieval import get_retriever, reload_index

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

UNANSWERED_FILE = DATA_DIR / "unanswered.jsonl"
LEADS_FILE = DATA_DIR / "leads.jsonl"

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "placidway-secret-admin-token-2026")

app = FastAPI(
    title="PlacidWay Knowledge Chatbot",
    description="Grounded website chatbot for PlacidWay medical tourism platform.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Schemas
class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'model' / 'assistant'")
    content: str = Field(..., max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User's query")
    history: List[ChatMessage] = Field(default_factory=list, description="Prior conversation turns")


class SourceItem(BaseModel):
    title: str
    url: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    answered: bool
    suggest_lead_capture: bool = False


class LeadRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=150)
    treatment: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=500)


def verify_admin(token: Optional[str]) -> bool:
    """Validate admin token against ADMIN_TOKEN environment variable."""
    if not token:
        return False
    # Support "Bearer <token>" or raw token
    clean_token = token.replace("Bearer ", "").strip()
    return clean_token == ADMIN_TOKEN


def log_unanswered_question(query: str, history: List[ChatMessage], reason: str = "out_of_corpus") -> None:
    """Logs unanswered questions to data/unanswered.jsonl with a UTC timestamp."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "history_length": len(history),
        "reason": reason,
    }
    try:
        with open(UNANSWERED_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.error("Failed to log unanswered question: %s", exc)


def is_cost_or_treatment_query(text: str, answer: str) -> bool:
    """Detect if query or answer touches medical costs, pricing, or treatment details."""
    combined = f"{text} {answer}".lower()
    keywords = [
        "cost", "price", "pricing", "$", "usd", "package", "treatment", "therapy",
        "program", "in-patient", "out-patient", "surgery", "cancer", "adenocarcinoma",
        "adrenal", "anal", "quote", "fee", "inclusions"
    ]
    return any(k in combined for k in keywords)


@app.get("/api/health")
def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring, uptime pings, and container checks."""
    retriever = get_retriever()
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "chunks_loaded": len(retriever.chunks),
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest) -> ChatResponse:
    """Processes visitor questions using query rewrite, BM25 retrieval, and grounded Gemini answering."""
    try:
        # Convert history format
        history_dicts = [{"role": m.role, "content": m.content} for m in req.history]

        result = generate_chat_response(
            message=req.message,
            history=history_dicts,
        )

        answered = result.get("answered", False)
        answer = result.get("answer", "")
        sources_data = result.get("sources", [])

        # Check if question could not be answered from the content
        if not answered:
            log_unanswered_question(
                query=req.message,
                history=req.history,
                reason="not_in_content_or_out_of_scope",
            )

        # Determine whether to suggest lead capture (non-blocking)
        suggest_lead = answered and is_cost_or_treatment_query(req.message, answer)

        sources = [SourceItem(title=s.get("title", ""), url=s.get("url", "")) for s in sources_data]

        return ChatResponse(
            answer=answer,
            sources=sources,
            answered=answered,
            suggest_lead_capture=suggest_lead,
        )

    except Exception as exc:
        logger.error("Error in /api/chat endpoint: %s", exc, exc_info=True)
        return ChatResponse(
            answer="I'm a bit busy, please try again in a moment.",
            sources=[],
            answered=False,
            suggest_lead_capture=False,
        )


@app.post("/api/lead")
def submit_lead(lead: LeadRequest) -> Dict[str, Any]:
    """Capture patient name and email for a free treatment/cost quote."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "name": lead.name.strip(),
        "email": lead.email.strip(),
        "treatment": lead.treatment.strip() if lead.treatment else None,
        "notes": lead.notes.strip() if lead.notes else None,
    }
    try:
        with open(LEADS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return {"status": "success", "message": "Thank you! Your quote request has been received."}
    except Exception as exc:
        logger.error("Failed to save lead: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to store lead request at this time."
        )


@app.post("/api/refresh")
def refresh_knowledge(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    admin_token_header: Optional[str] = Header(None, alias="ADMIN_TOKEN"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Dict[str, Any]:
    """
    Protected endpoint to re-run ingestion from the 7 URLs and reload the BM25 index
    without restarting the server process. Requires ADMIN_TOKEN header.
    """
    token = x_admin_token or admin_token_header or authorization
    if not verify_admin(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: valid ADMIN_TOKEN header required."
        )

    logger.info("Admin triggered knowledge refresh. Running ingestion...")
    ingest_result = run_ingestion()
    new_count = reload_index()

    return {
        "status": "success",
        "message": f"Ingestion completed and BM25 index reloaded with {new_count} chunks.",
        "ingest_stats": ingest_result,
    }


@app.get("/api/admin/unanswered")
def get_unanswered_questions(
    token: Optional[str] = Query(None),
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> List[Dict[str, Any]]:
    """Protected API to return unanswered queries from data/unanswered.jsonl."""
    auth_token = token or x_admin_token or authorization
    if not verify_admin(auth_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: valid ADMIN_TOKEN required."
        )

    if not UNANSWERED_FILE.exists():
        return []

    entries = []
    with open(UNANSWERED_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
    return entries[::-1]  # Most recent first


@app.get("/admin", response_class=HTMLResponse)
def admin_page(token: Optional[str] = Query(None)) -> HTMLResponse:
    """Simple, clean administrative dashboard for reviewing unanswered questions and triggering index refresh."""
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PlacidWay Bot Admin</title>
  <style>
    :root {{
      --bg: #fbfbfc;
      --card-bg: #ffffff;
      --text: #1c1d1f;
      --muted: #6e6e73;
      --accent: #1d6b5e;
      --border: rgba(0, 0, 0, 0.08);
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #161718;
        --card-bg: #1f2022;
        --text: #f5f5f7;
        --muted: #a1a1a6;
        --accent: #2a8c7b;
        --border: rgba(255, 255, 255, 0.08);
      }}
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif;
      background-color: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 32px 16px;
      line-height: 1.5;
    }}
    .container {{
      max-width: 800px;
      margin: 0 auto;
    }}
    h1 {{
      font-size: 24px;
      font-weight: 600;
      letter-spacing: -0.5px;
      margin-bottom: 8px;
    }}
    p.subtitle {{
      color: var(--muted);
      margin-top: 0;
      margin-bottom: 24px;
      font-size: 15px;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 24px;
    }}
    .auth-bar {{
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
    }}
    input[type="text"] {{
      flex: 1;
      padding: 10px 14px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--card-bg);
      color: var(--text);
      font-size: 14px;
    }}
    button {{
      background: var(--accent);
      color: white;
      border: none;
      border-radius: 8px;
      padding: 10px 18px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
    }}
    button:hover {{
      opacity: 0.9;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      text-align: left;
      padding: 12px 8px;
      border-bottom: 1px solid var(--border);
    }}
    th {{
      color: var(--muted);
      font-weight: 500;
    }}
    .status-msg {{
      margin-top: 12px;
      font-size: 14px;
      color: var(--accent);
    }}
  </style>
</head>
<body>
  <div class="container">
    <h1>PlacidWay Knowledge Base Admin</h1>
    <p class="subtitle">Review unanswered visitor questions and trigger live knowledge index reloads.</p>

    <div class="card">
      <div class="auth-bar">
        <input type="text" id="tokenInput" placeholder="Enter ADMIN_TOKEN" value="{token or ''}">
        <button onclick="loadUnanswered()">Load Data</button>
        <button onclick="triggerRefresh()">Re-run Ingestion</button>
      </div>
      <div id="statusMsg" class="status-msg"></div>
    </div>

    <div class="card">
      <h2 style="font-size: 18px; margin-top: 0;">Unanswered Questions Log</h2>
      <div id="unansweredList">
        <p style="color: var(--muted);">Click 'Load Data' to fetch recorded unanswered questions.</p>
      </div>
    </div>
  </div>

  <script>
    async function loadUnanswered() {{
      const token = document.getElementById('tokenInput').value.trim();
      const status = document.getElementById('statusMsg');
      if (!token) {{
        status.textContent = 'Please enter ADMIN_TOKEN.';
        return;
      }}
      status.textContent = 'Loading...';
      try {{
        const res = await fetch('/api/admin/unanswered?token=' + encodeURIComponent(token));
        if (!res.ok) throw new Error('Unauthorized or error ' + res.status);
        const data = await res.json();
        status.textContent = 'Loaded ' + data.length + ' entries.';
        if (data.length === 0) {{
          document.getElementById('unansweredList').innerHTML = '<p style=\"color: var(--muted);\">No unanswered questions logged yet.</p>';
          return;
        }}
        let html = '<table><thead><tr><th>Time</th><th>Question</th><th>Reason</th></tr></thead><tbody>';
        data.forEach(item => {{
          const d = new Date(item.timestamp).toLocaleString();
          html += '<tr><td style=\"white-space:nowrap; color:var(--muted);\">' + d + '</td><td><strong>' + escapeHtml(item.query) + '</strong></td><td>' + (item.reason || '') + '</td></tr>';
        }});
        html += '</tbody></table>';
        document.getElementById('unansweredList').innerHTML = html;
      }} catch (err) {{
        status.textContent = 'Error: ' + err.message;
      }}
    }}

    async function triggerRefresh() {{
      const token = document.getElementById('tokenInput').value.trim();
      const status = document.getElementById('statusMsg');
      if (!token) {{
        status.textContent = 'Please enter ADMIN_TOKEN to refresh.';
        return;
      }}
      status.textContent = 'Triggering ingestion and re-indexing. Please wait...';
      try {{
        const res = await fetch('/api/refresh', {{
          method: 'POST',
          headers: {{ 'X-Admin-Token': token }}
        }});
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Error ' + res.status);
        status.textContent = 'Success: ' + data.message;
      }} catch (err) {{
        status.textContent = 'Refresh failed: ' + err.message;
      }}
    }}

    function escapeHtml(str) {{
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }}

    // Auto-load if token in query string
    if (document.getElementById('tokenInput').value) {{
      loadUnanswered();
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


# Mount static directory for frontend assets
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=FileResponse)
def serve_index() -> FileResponse:
    """Serve the main chatbot UI."""
    index_file = STATIC_DIR / "index.html"
    return FileResponse(index_file)
