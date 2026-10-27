# PlacidWay Medical Tourism Knowledge Chatbot

A production-quality, strictly-grounded website knowledge chatbot for **PlacidWay** (medical tourism platform). Built as a take-home assessment, this chatbot answers visitor inquiries using **ONLY** verified content from 7 designated PlacidWay pages. It enforces strict factual grounding, never invents prices or clinics, handles follow-ups and multilingual questions, and features a calm, human-designed Apple-style interface.

---

## 🌟 Key Features

1. **Strictly Grounded Knowledge Base**:
   - Indexed strictly from 7 designated PlacidWay pages (ITC Tijuana clinic profile, adenocarcinoma, adrenal, and anal cancer treatment packages, clinic videos, price list, and alternative medicine price comparison).
   - Never hallucinates prices, claims, or procedures. If content is missing, it honestly states "I don't know" and directs users to PlacidWay's free quote form.
2. **Apple-Inspired Human UI**:
   - Built with Vanilla HTML5, CSS3, and JavaScript (no frameworks, no bundlers, zero build steps).
   - Calm, warm healthcare aesthetic with system font stack, soft off-white surfaces, hairline borders, and a tranquil sage/teal accent.
   - iMessage-style bubbles, 3-dot typing indicator, starter question pills, source link pills, and automatic light/dark mode support (`prefers-color-scheme`).
   - Fully responsive down to 375px mobile screens.
3. **Free-Tier Safety & Resilience**:
   - Exponential backoff retry loop handling 429 and 5xx API spikes.
   - In-memory query cache preventing duplicate model calls.
   - At most 2 model calls per message; skips rewrite call entirely on first English messages.
   - Friendly in-chat fallback message (`"I'm a bit busy, please try again in a moment"`) instead of raw error traces.
4. **Non-Blocking Lead Capture**:
   - Automatically surfaces a subtle quote request card after cost or treatment queries without blocking the conversation.
   - Appends patient contact details to `data/leads.jsonl`.
5. **Admin Monitoring & Live Refresh**:
   - Logs unanswerable or out-of-scope queries to `data/unanswered.jsonl`.
   - Protected web dashboard at `/admin` (secured with `ADMIN_TOKEN`).
   - Live knowledge re-indexing endpoint (`POST /api/refresh`) without process restart.

---

## 🏗️ Architecture & Pipeline

```
[ User Query + History ]
           │
           ▼
[ Step 1: Query Rewrite ] (Gemini API / JSON mode)
   ├─ Skipped if first message & English
   └─ Outputs: standalone_query_in_english, user_language
           │
           ▼
[ Step 2: BM25 Retrieval ] (rank_bm25 over data/knowledge.json)
   ├─ Tokenizes query & filters English stopwords
   ├─ Scores 70 structured chunks (target 200-350 words)
   └─ If best_score < 1.0 -> flags as out-of-corpus
           │
           ▼
[ Step 3: Answer Generation ] (Gemini API with Strict System Prompt)
   ├─ Enforces 11 grounding rules (prices with currency, links, disclaimers)
   ├─ Out-of-scope / booking requests politely declined
   └─ Replies in user's detected language with clean markdown sources
```

---

## 🛠️ Technology Stack & Rationale

| Component | Technology | Rationale |
|---|---|---|
| **Backend** | Python 3.11 & FastAPI | High performance, async native, type-safe, minimal memory overhead. |
| **Frontend** | Vanilla HTML, CSS, JS | Zero build steps, instant load times, clean hand-crafted Apple aesthetics. |
| **LLM Provider** | Google Gemini (`google-genai` SDK) | Uses `gemini-2.5-flash` for high factual accuracy, rapid inference, and native JSON mode. |
| **Retrieval** | `rank-bm25` (BM25Okapi) | Deterministic sparse keyword retrieval; optimal for tiny, exact-token corpuses without vector DB overhead. |
| **Ingestion** | `trafilatura`, `BeautifulSoup4`, `langdetect` | Removes boilerplate and navbars, converts pricing tables to clean Markdown, verifies English-only text. |
| **Server** | `uvicorn` | High-throughput ASGI server. |

---

## 🚀 Setup & Local Installation

### Prerequisites
- Python 3.11+
- A Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/))

### 1. Clone & Setup Virtual Environment
```bash
git clone <repository_url>
cd chatbot-placidway

# Create virtual environment
python -m venv .venv

# Activate environment
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Edit `.env` with your credentials:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
ADMIN_TOKEN=placidway-secret-admin-token-2026
CONTACT_EMAIL=candidate@assessment.com
```

### 3. Run Ingestion (Optional — `data/knowledge.json` is Pre-Committed)
The knowledge base is already pre-ingested into `data/knowledge.json`. To run fresh ingestion:
```bash
python ingest.py
```

### 4. Start the Application
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser to:
- **Chatbot UI:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Admin Dashboard:** [http://127.0.0.1:8000/admin?token=placidway-secret-admin-token-2026](http://127.0.0.1:8000/admin?token=placidway-secret-admin-token-2026)
- **API Health:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## 🧪 Running Automated Tests

An automated test suite evaluates the 8 mandatory test categories (Cost, Comparison, Procedure, Follow-up, Booking/Not in content, Out of scope, Medical advice, and Trick question):

```bash
python test_questions.py
```
This runs the full suite with 6-second pauses between queries to protect Gemini free-tier rate limits and automatically writes transcripts to `TEST_RESULTS.md`.

---

## 🔄 Refreshing Knowledge Base in Production

You can trigger a live re-ingestion and index reload without restarting the server:

```bash
curl -X POST http://127.0.0.1:8000/api/refresh \
  -H "X-Admin-Token: placidway-secret-admin-token-2026"
```
Or use the **"Re-run Ingestion"** button directly on the `/admin` page.

---

## ☁️ Deployment on Render

This project includes a native `render.yaml` specification for single-service deployment.

1. Push this repository to GitHub.
2. In Render, select **New +** -> **Blueprint** and connect your repository.
3. Set the environment variable `GEMINI_API_KEY` in the Render dashboard.
4. Render will run `pip install -r requirements.txt` and start with `uvicorn main:app --host 0.0.0.0 --port $PORT`.

> [!NOTE]
> **Keeping Free Render Instances Awake for 7 Days:**  
> Free Render web services spin down after 15 minutes of inactivity. To keep your assessment instance awake continuously for 7 days, configure a free HTTP monitor (such as [UptimeRobot](https://uptimerobot.com) or [Cron-Job.org](https://cron-job.org)) to send an HTTP GET request to `https://<your-service>.onrender.com/api/health` every 10 minutes.

---

## ⚠️ Known Limitations
See [WRITEUP.md](WRITEUP.md) for a comprehensive discussion of architectural trade-offs, keyword sensitivity under pure BM25, and high-impact improvements planned for future iterations.
