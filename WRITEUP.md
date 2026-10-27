# Engineering Reflection & Future Improvements

**Project:** PlacidWay Medical Tourism Knowledge Chatbot  
**Assessment Period:** 1-day implementation  

---

## 1. What I Would Improve With Another Week

### A. Advanced Hybrid Retrieval (Dense + Sparse Hybrid)
While BM25 is remarkably effective and predictable for small, exact-token corpuses (such as medical procedure names, clinic titles, and explicit pricing tables), users often express symptoms in colloquial, indirect terms (e.g., *"lumps in throat"* for thyroid cancer or *"holistic alternative"* for immunotherapy). With another week, I would implement **Reciprocal Rank Fusion (RRF)** pairing BM25 with a lightweight dense embedding model (e.g., `text-embedding-004` or local `bge-small-en-v1.5`). Dense retrieval captures semantic intent, while BM25 guarantees exact keyword and price term preservation.

### B. High-Fidelity Table Extraction & Structured Pricing Schema
In the current implementation, pricing tables are converted into clean Markdown tables during ingestion. While this works well for language models, medical tourism pricing frequently involves complex tiers: Out-Patient vs. In-Patient, inclusions, exclusions, and per-day costs. I would build a dedicated structured extraction pass using Pydantic schemas to store prices as relational records (`procedure`, `clinic_name`, `country`, `in_patient_cost_usd`, `out_patient_cost_usd`, `duration_weeks`, `inclusions_list`). Retrieval could then execute deterministic SQL/JSON queries for price comparisons, entirely eliminating hallucination risk.

### C. Evaluation Framework & Grounding Benchmark
I would implement an automated evaluation suite using synthetic evaluation datasets (e.g., Ragas or DeepEval) measuring:
1. **Faithfulness / Hallucination Rate:** Ensuring 100% of facts in the answer map to retrieved chunks.
2. **Context Precision & Recall:** Testing whether BM25 returns the optimal chunks for multi-turn questions.
3. **Safety & Medical Disclaimers:** Automated tests verifying that every question mentioning a symptom or condition correctly receives a doctor referral and disclaimer.

### D. Streaming Answers (SSE / WebSockets)
To improve perceived latency on low-bandwidth mobile connections, I would implement Server-Sent Events (`StreamingResponse` in FastAPI) with Gemini's streaming API (`generate_content_stream`), allowing tokens to stream into the iMessage bubble with smooth character reveals.

### E. Multi-Lingual Ingestion Cache
Currently, non-English visitors have their queries translated to English for BM25 retrieval and translated back by Gemini during answer generation. Translating the corpus into key medical tourism languages (Spanish, Arabic) in advance would enable native retrieval in the user's native tongue.

---

## 2. Known Limitations

1. **Tiny Corpus Boundary:** The bot's knowledge is strictly bounded to the 7 designated URLs. Questions regarding other medical specialties (e.g., plastic surgery, dental implants in Costa Rica), insurance coverage, or travel visa policies will appropriately result in *"I don't know"*, as required by design.
2. **Dynamic Web Structure Dependency:** If PlacidWay updates its HTML layout or adds heavy JavaScript rendering that hides table cells, Trafilatura and BeautifulSoup require re-verifying CSS selectors.
3. **Gemini Free-Tier Rate Limits:** The Gemini free tier is subject to 15 Requests Per Minute (RPM) and daily quotas. Although our exponential backoff, in-memory caching, and query rewrite skipping safeguard against bursts, high concurrent traffic requires upgrading to a standard tier or adding Redis queueing.
4. **Keyword Sensitivity of Pure BM25:** If a user makes spelling errors or uses terminology completely absent from the 7 pages without giving context, BM25 scores may fall below the threshold unless rewritten accurately in Step 1.
