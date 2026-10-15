# SATARKA HEALTH INTELLIGENCE & MISINFORMATION VERIFICATION PLATFORM
## Comprehensive Technical Architecture, Codebase Analysis, Security Report, and College Viva Defense Guide

**Project Name:** Satarka (Satarka Hybrid Verification API & Health Intelligence Platform - v3.0.0)  
**IDE / Form Factor:** Opened in Android Studio (Full-Stack Python FastAPI + React/Vite + SQLite + FAISS + PyTorch/Transformers)  
**Date:** October 2026  
**Document Version:** 3.0.0  

---

## TABLE OF CONTENTS
1. Cover & Executive Overview
2. Table of Contents
3. Project Overview
4. Architecture Analysis & Workflow Diagrams
5. Complete Component Breakdown
6. Technology Stack & Dependencies Analysis
7. Database Schema & Data Analysis
8. API Endpoint Analysis
9. AI/ML Pipeline & Model Analysis
10. Screen-by-Screen UI Analysis
11. Security & Privacy Analysis
12. Presentation Notes (2-Min, 5-Min, 10-Min & Demo Walkthrough)
13. Comprehensive Viva Questions & Answers (30 Basic, 30 Intermediate, 30 Advanced)
14. Faculty Trick Questions & Expert Defense Strategies
15. Project Defense Guide (Must-Know Files, Algorithms & Concepts)
16. Resume & Interview Value
17. Revision Notes & Key Points Cheat Sheet

---

# SECTION 1: PROJECT OVERVIEW

### 1. Project Name
**Satarka (Satarka Hybrid Verification API & Health Intelligence Platform - v3.0.0)**

### 2. Project Purpose
Satarka is an enterprise-grade, privacy-first, hybrid AI-powered healthcare platform designed to combat health misinformation, verify medical claims with live evidence, analyze personal lab reports through local OCR (Optical Character Recognition), perform AI-based symptom assessments, and manage longitudinal medical trends without transmitting sensitive patient data to third-party services.

### 3. Problem Statement
Medical misinformation spreads rapidly online, leading to unverified treatments, vaccine hesitancy, and dangerous health practices. Concurrently, patients struggle to organize and understand their personal laboratory reports (e.g., Blood Sugar, HbA1c, Lipid Profiles, CBC), track medical metrics over time, or obtain quick, privacy-focused symptom evaluations without exposing private health records to cloud trackers.

### 4. Real-World Problem Solved
1. **Automated Misinformation Verification:** Instantly checks online medical claims (e.g., *"Antibiotics cure the common cold"*) against verified scientific datasets, live Tavily web search, Google Fact Check Tools API, domain WHOIS records, and SSL trust indicators.
2. **Privacy-Preserving Lab Report Analysis:** Extracts structured numerical laboratory measurements from uploaded PDFs and images locally using `pypdf` and `pytesseract` (Tesseract OCR), enabling patients to search, visualize trends, and ask natural language questions about their health data locally.
3. **AI-Driven Symptom Evaluation:** Uses Microsoft PubMedBERT embeddings (`microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext`) and Logistic Regression to match symptoms to disease profiles while giving risk levels, prevention steps, and clinical disclaimers.
4. **Autonomous Dataset Continuous Fine-Tuning:** Ingests high-confidence verified claims into a local Qwen2.5-0.5B-Instruct LoRA fine-tuning queue for domain-specific local LLM adaptation.

### 5. Target Users
- **General Public & Patients:** Individuals seeking to verify health claims, understand medical lab test results, or evaluate symptoms privately.
- **Healthcare Researchers & Fact-Checkers:** Professionals verifying medical claims against peer-reviewed evidence and government health sources (WHO, CDC).
- **Clinical Administrators:** Technical admins managing claim review dashboards, inspecting model accuracy, and overseeing local training pipelines.

### 6. Main Features
- **Health Claim Classifier (`POST /health/predict`):** Local ML model using TF-IDF + Logistic Regression with health domain filtering.
- **Misinformation Detection with RAG & Web Evidence (`POST /query`):** FAISS semantic vector retrieval combined with multi-tier LLM routing (Groq Llama 3.1 8B, Groq Llama 3.3 70B, OpenRouter GPT-OSS 120B) and Tavily web evidence synthesis.
- **Independent Evidence Validator (`app/services/validator.py`):** Scores evidence on 5 weighted pillars: Relevance (30%), Source Authority (25%), Evidence Agreement (20%), Recency (15%), and Domain Independence (10%).
- **Personal Health Records & OCR Processing (`POST /personal-reports/upload`):** PDF text extraction and Tesseract image OCR with TF-IDF/Logistic test classifier, measurement parsing, and trend analysis.
- **Deterministic Record Q&A (`POST /personal-reports/ask`):** Answers natural language queries regarding historical lab value changes (e.g., *"How has my blood sugar changed?"*).
- **Symptom Checker (`POST /symptom-check`):** Image OCR + PubMedBERT transformer embedding classifier with fallback rule-based matching and SQLite caching (`symptoms_db`).
- **Admin Review & Fine-Tuning Pipeline (`POST /training/run`):** Human-in-the-loop claim approval workflow and 4-bit NF4 quantized BitsAndBytes + TRL `SFTTrainer` LoRA fine-tuning for Qwen2.5-0.5B-Instruct.

### 7. Expected Outcomes
- Reduction in health misinformation exposure with actionable validation scores (0–100%).
- Complete data privacy for medical report storage and local analysis.
- Instant, structured medical metric trend tracking across multiple health reports.

---

# SECTION 2: PROJECT WORKFLOW & DIAGRAMS

### 1. Complete System Execution Flow Diagram

```
+-----------------------------------------------------------------------------------+
|                                 USER INPUT (React UI)                             |
+-----------------------------------------------------------------------------------+
       |                                  |                                  |
       v                                  v                                  v
[1. Health Claim Check]        [2. Query Verification]            [3. Report Upload]
       |                                  |                                  |
       v                                  v                                  v
Domain Filter check             FAISS Vector Index                 pypdf / Tesseract OCR
(is_health_related)             (all-MiniLM-L6-v2)                        |
       |                                  |                                  v
       v                     +------------+------------+            TF-IDF Test Classifier
TF-IDF + Logistic            | Similarity >= 0.88?     |            + Lab Regex Parser
Regression Model             +------------+------------+                     |
       |                                  |                                  v
       v                         (Yes) /     \ (No)                 Save to SQLite
Return Verdict + Probabilities         v       v                    (personal_reports +
                             Return Fast    Multi-Tier LLM           personal_measurements)
                             Dataset Hit    Routing + Tavily Search          |
                                                   |                         v
                                                   v                Trend Summary & Q&A
                                            5-Pillar Validator               |
                                                   |                         v
                                                   v                 Return to Frontend
                                            Ingest if >= 95%
```

---

# SECTION 3: ARCHITECTURE ANALYSIS

### 1. Architectural Pattern Used
**Clean Architecture with Layered Domain Service Pattern & Hybrid Local/Cloud RAG Pipeline**

```
+-----------------------------------------------------------------------------------+
|                              PRESENTATION LAYER (UI)                              |
|                          React 18 + Vite (App.jsx) + CSS                          |
+-----------------------------------------------------------------------------------+
                                          |
                                          v  REST API (JSON / Multipart)
+-----------------------------------------------------------------------------------+
|                              CONTROLLER LAYER (API)                               |
|                         FastAPI Router (app/main.py)                              |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                                 SERVICE LAYER                                     |
|  * validator.py          * health_model.py          * symptom_checker.py          |
|  * personal_records.py   * evidence_reasoner.py      * llm.py & search.py          |
+-----------------------------------------------------------------------------------+
                             /                    \
                            v                      v
+---------------------------------------+  +----------------------------------------+
|              DATA LAYER               |  |              AI/ML LAYER               |
|  * SQLite Engine (app/db.py)          |  |  * FAISS Index (app/dataset.py)        |
|  * File Storage (data/personal_rep)   |  |  * PubMedBERT & SentenceTransformers    |
|  * Cache (faiss_index.bin / pkl)      |  |  * Scikit-Learn Classifiers            |
|                                       |  |  * Hugging Face TRL / LoRA Pipeline    |
+---------------------------------------+  +----------------------------------------+
```

---

# SECTION 4: COMPLETE COMPONENT BREAKDOWN

| Component / Module | Path / File | Purpose | Key Classes / Functions | Interactions |
| :--- | :--- | :--- | :--- | :--- |
| **API Entrypoint** | `app/main.py` | Primary FastAPI application, middleware, route handlers | `app`, `lifespan()`, `query()`, `upload_personal_report()` | Connects UI to Service & Data layers |
| **Config Manager** | `app/config.py` | Environment variable loader & settings singleton | `Settings`, `settings()` | Injected across all modules |
| **Database Engine** | `app/db.py` | SQLite schema management, connection factory, CRUD | `init_db()`, `connection()`, `log_query()`, `upsert_claim()`, `create_personal_report()` | Interacts with SQLite database file |
| **Pydantic Schemas** | `app/models.py` | Request/Response DTO validation schemas | `QueryRequest`, `QueryResponse`, `HealthPredictionRequest`, `PersonalRecordQuestion` | Validates API input/output data |
| **FAISS Vector Engine**| `app/dataset.py` | Dense vector indexing and semantic retrieval | `get_top_k_matches()`, `refresh_index()`, `get_model()` | Uses `SentenceTransformer`, writes binary index |
| **Evidence Validator** | `app/services/validator.py` | Scored mathematical evidence verification engine | `validate()`, `score()`, `authority()`, `recency()`, `_domain_reputation()` | Calls LLM, Whois, Google Fact Check |
| **Health Classifier** | `app/services/health_model.py` | Local TF-IDF + Logistic Regression claim model | `predict_health_claim()`, `train_health_model()`, `is_health_related()` | Uses Scikit-Learn, joblib |
| **Symptom Checker** | `app/services/symptom_checker.py`| Bio-transformer symptom diagnostic service | `symptom_checker()`, `_predict_disease()`, `_extract_ocr_text()` | Uses PubMedBERT, Tesseract OCR |
| **Personal Records** | `app/services/personal_records.py`| Lab report OCR parser & TF-IDF test classifier | `extract_report_text()`, `classify_test_type()`, `extract_measurements()` | Uses PyPDF, Tesseract, Pillow, Regex |
| **LLM Connector** | `app/services/llm.py` | Multi-provider LLM API router (Groq/OpenRouter) | `call()`, `choose_route()`, `cfg()` | Interacts with OpenAI SDK |
| **Search Gateway** | `app/services/search.py` | External search gateway for real-time web context | `search()` | Calls Tavily HTTP API via `httpx` |
| **Training Pipeline** | `app/training/pipeline.py` | Quantized LoRA fine-tuning engine | `train_if_ready()`, `export_jsonl()`, `_evaluate_model()` | Uses Hugging Face Transformers, TRL, PEFT |
| **React UI App** | `frontend/src/App.jsx` | Full client single-page application UI | `App()`, `predict()`, `verifyWithSources()`, `loadPersonalRecords()` | Communicates with FastAPI via HTTP `fetch` |

---

# SECTION 5: TECHNOLOGIES USED & DEPENDENCIES

### Dependencies Analysis (`requirements.txt`)
- `fastapi>=0.115,<1`: High performance async API framework.
- `uvicorn[standard]>=0.30,<1`: Asynchronous ASGI web server.
- `openai>=1.70,<3`: Universal client library for OpenAI-compatible APIs (Groq, OpenRouter).
- `httpx>=0.27,<1`: Asynchronous HTTP client for external API requests (Tavily).
- `scikit-learn>=1.5,<2`: Machine learning library powering TF-IDF vectorizers and Logistic Regression.
- `joblib>=1.3,<2`: Fast serialization framework for model persistent storage.
- `pydantic>=2.7,<3`: Runtime data validation and typing system.
- `sentence-transformers>=3.0`: Embedding generation library (`all-MiniLM-L6-v2`).
- `torch>=2.2,<3`: PyTorch deep learning framework.
- `pillow>=10.0.0`: Image processing engine for OCR.
- `pytesseract>=0.3.10`: Local wrapper for Tesseract OCR engine.
- `pypdf>=4.0.0`: Pure Python offline PDF text extractor.
- `faiss-cpu>=1.8,<2`: Facebook AI Similarity Search vector library.
- `python-whois>=0.9.0`: Domain registration lookup for domain age evaluation.

---

# SECTION 6: DATABASE ANALYSIS

### Schema Architecture
The SQLite database (`data/satarka.db`) manages 8 relational tables:
1. `verified_claims`: Canonical health claims, verified answers, verdict, validation score, model used, sources JSON.
2. `claim_reviews`: Admin review logs and review notes.
3. `training_examples`: Approved training pairs (prompt/completion) for model fine-tuning.
4. `training_runs`: Fine-tuning run logs, base model name, training metrics JSON.
5. `query_log`: Historical query logs, route used, model used, validation score, verdict, answer payload.
6. `personal_reports`: Metadata for user uploaded lab reports (filename, file path, test type, extraction method, patient name, date).
7. `personal_measurements`: Extracted lab metrics (test name, raw value, numeric value, unit, reference low/high, status).
8. `symptoms_db`: Local cache for symptom-to-disease mappings.

---

# SECTION 7: API ENDPOINTS ANALYSIS

| Endpoint | Method | Input | Output |
| :--- | :--- | :--- | :--- |
| `/health/predict` | POST | `{"claim": "..."}` | Verdict, confidence, probability breakdown |
| `/query` | POST | `{"query": "..."}` | Answer, verdict, validator score, sources, evidence |
| `/symptom-check` | POST | Form (`symptoms`, `image`) | Disease, risk level, prevention, OCR text |
| `/personal-reports/upload` | POST | File (PDF/PNG/JPG/WEBP) | Report ID, extracted measurements |
| `/personal-reports/summary` | GET | `query` (optional) | Aggregated lab metrics trend analysis |
| `/personal-reports/ask` | POST | `{"question": "..."}` | Natural language delta answer on saved lab records |
| `/dataset/search` | POST | `{"query": "...", "k": 5}` | FAISS top-K semantic matches |
| `/report` | GET | `limit` (int) | Historical query log summary & query list |
| `/admin/review` | POST | `{"claim_id": 1, "status": "approved"}` | Sets claim review status |
| `/training/run` | POST | `force` (bool) | Triggers LoRA fine-tuning run |

---

# SECTION 8: AI/ML ANALYSIS

### Complete AI Pipeline
1. **Domain Term Filtering (`is_health_related`):** Fast dictionary scan for health terminology.
2. **Local Health Classifier (`health_claim_model.joblib`):** TF-IDF Vectorizer + Logistic Regression.
3. **Dense Vector Search (`all-MiniLM-L6-v2` + `FAISS`):** Generates 384-dimensional embeddings and executes inner product cosine distance search ($L2$ normalized).
4. **Bio-Symptom Transformer (`PubMedBERT`):** Embeds symptom text into high-dimensional medical representation space to predict disease profiles.
5. **Continuous Fine-Tuning (`Qwen2.5-0.5B-Instruct`):** 4-bit NF4 quantized BitsAndBytes + TRL `SFTTrainer` with PEFT LoRA ($r=16, \alpha=32$).

---

# SECTION 9: SCREEN-BY-SCREEN ANALYSIS

1. **Claim Verification View:** Input textarea, predict button, confidence gauge, probability distribution bars.
2. **Misinformation Detection View:** Live web verification, cited source links, 5-pillar score badge.
3. **Symptom Checker View:** File upload drop zone, symptom input, assessment card, detected symptom pills.
4. **Personal Health Records View:** Report list sidebar, lab measurement table, trend cards with direction deltas, record Q&A.
5. **Query History View:** Query audit trail, verdict distribution chart, chronological log entries.

---

# SECTION 10: SECURITY ANALYSIS

1. **Privacy-First Local Storage:** Reports and extracted lab values are stored 100% locally in `data/personal_reports` and `satarka.db`.
2. **Path Traversal Protection:** Absolute path resolving (`.resolve()`) verifies targets stay inside the designated directory before file deletion.
3. **Upload File Validation:** File extensions, MIME headers, byte sizes (10MB limit), and PDF/Image signatures are validated.
4. **SQL Parameterization:** All SQLite queries use parameterized placeholders (`?`) to completely block SQL injection.

---

# SECTION 11: PRESENTATION NOTES

### 2-Minute Elevator Pitch
> "Good morning, panel. Today I present Satarka—an AI-driven healthcare intelligence and misinformation verification platform. Satarka solves two pressing problems: online medical misinformation and personal lab report confusion. First, it verifies health claims using local vector search, web retrieval, and a 5-pillar mathematical validation model scoring authority, recency, and agreement. Second, it includes a 100% offline Personal Health Record parser that extracts lab test values from PDFs and images using local Tesseract OCR, tracks health trends, and answers natural language questions about test changes—all without cloud data leakage. Thank you."

---

# SECTION 12: VIVA QUESTIONS & ANSWERS

### Basic Questions (1–10)
1. **Q: What is Satarka?**  
   **A:** A hybrid AI healthcare platform for health claim verification, medical report parsing, and symptom analysis.
2. **Q: What framework is used for the backend?**  
   **A:** FastAPI (Python).
3. **Q: What database is used?**  
   **A:** Embedded SQLite (`data/satarka.db`).
4. **Q: What vector search engine is integrated?**  
   **A:** Facebook AI Similarity Search (FAISS).
5. **Q: What embedding model generates vectors?**  
   **A:** `sentence-transformers/all-MiniLM-L6-v2`.
6. **Q: How are image reports processed?**  
   **A:** Via Tesseract OCR (`pytesseract`) and Pillow locally.
7. **Q: How are PDF reports read?**  
   **A:** Via `pypdf.PdfReader` locally.
8. **Q: What frontend framework is used?**  
   **A:** React 18 built with Vite.
9. **Q: What transformer model is used for symptoms?**  
   **A:** `microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext`.
10. **Q: What is the similarity threshold for a dataset hit?**  
    **A:** 0.88 cosine similarity.

### Intermediate Questions (11–20)
11. **Q: What are the 5 pillars of the validator score?**  
    **A:** Relevance (30%), Source Authority (25%), Agreement (20%), Recency (15%), Independence (10%).
12. **Q: How is domain authority computed?**  
    **A:** Based on source classification (e.g. WHO=100, Gov=95) adjusted by WHOIS age and SSL trust.
13. **Q: What happens if validation score >= 95%?**  
    **A:** The claim is auto-ingested into `verified_claims` and queued for fine-tuning.
14. **Q: How does multi-tier LLM routing work?**  
    **A:** Queries are routed to Cheap (`llama-3.1-8b`), Medium (`llama-3.3-70b`), or Premium (`gpt-oss-120b`) based on query complexity.
15. **Q: How does `personal_reports_summary` track trends?**  
    **A:** It aggregates measurements across dates, computes value deltas ($Latest - First$), and identifies direction.
16. **Q: What quantization method is used for local fine-tuning?**  
    **A:** 4-bit NormalFloat (NF4) quantization via BitsAndBytes.
17. **Q: What role does `symptoms_db` play?**  
    **A:** It caches canonical symptom-to-disease mappings to skip model inference on exact matches.
18. **Q: How are lab test values parsed from text?**  
    **A:** Using structured regular expressions targeting test names, numbers, units, and reference ranges.
19. **Q: How are non-medical inputs handled?**  
    **A:** Domain term filtering classifies non-health text as `INVALID_STATEMENT`.
20. **Q: How is vector search accelerated in FAISS?**  
    **A:** Vectors are $L2$-normalized and indexed using `IndexFlatIP` for inner-product matrix multiplication.

### Advanced Questions (21–30)
21. **Q: What is the mathematical validation formula?**  
    **A:** $\text{Score} = 0.30 \cdot \text{Rel} + 0.25 \cdot \text{Auth} + 0.20 \cdot \text{Agree} + 0.15 \cdot \text{Rec} + 0.10 \cdot \text{Indep}$.
22. **Q: How is fine-tuning evaluated?**  
    **A:** Using ROUGE-L, ROUGE-2, and BLEU metrics calculated against validation prompt completions.
23. **Q: Why use LoRA fine-tuning?**  
    **A:** Low-Rank Adaptation trains low-rank matrices ($r=16$) while freezing base weights, enabling local GPU training.
24. **Q: How is path traversal mitigated during file deletion?**  
    **A:** Target paths are resolved using `.resolve()` and checked against `PERSONAL_REPORTS_DIR`.
25. **Q: Why use `sublinear_tf` in TF-IDF?**  
    **A:** It replaces term frequency $tf$ with $1 + \log(tf)$ to prevent term frequency dominance in long text.
26. **Q: How are conflicting web sources handled?**  
    **A:** The validator marks the status as `CONFLICTING` and sets verdict to `UNCERTAIN`.
27. **Q: What is the fallback mechanism if an LLM route fails?**  
    **A:** It automatically falls back across the order `[cheap -> medium -> premium]`.
28. **Q: How is self-validation bias avoided?**  
    **A:** Answer generation and validation use separate prompts; the validator depends strictly on retrieved external evidence.
29. **Q: How does `refresh_index()` maintain vector index consistency?**  
    **A:** It checks a DB state token (`count_maxUpdated`). If changed, it rebuilds embeddings and atomic binary files.
30. **Q: Why combine rule-based checks with AI models?**  
    **A:** Rules guarantee medical safety boundary enforcement, while AI models provide natural language generalization.

---

# SECTION 13: FACULTY TRICK QUESTIONS & DEFENSE ANSWERS

1. **Examiner:** *"Why not use Cloud Vision API for OCR?"*  
   **Answer:** *"Cloud OCR sends private patient lab reports to cloud servers, breaking medical privacy. Satarka processes all PDFs and images 100% offline using PyPDF and Tesseract OCR."*
2. **Examiner:** *"Why use Logistic Regression instead of Deep Learning for claim classification?"*  
   **Answer:** *"Logistic Regression with TF-IDF provides sub-millisecond CPU inference time with zero memory footprint for initial domain screening. Complex deep learning is reserved for PubMedBERT symptom embeddings and LLM reasoning."*
3. **Examiner:** *"What if Tavily returns biased or fake news websites?"*  
   **Answer:** *"Satarka does not trust search results blindly. It evaluates source WHOIS age, SSL certificate trust, domain classification, and cross-source agreement through a mathematical 5-pillar validator."*

---

# SECTION 14: PROJECT DEFENSE GUIDE

### Most Important Files to Master
- `app/main.py`: Route coordination and execution flow.
- `app/services/validator.py`: Mathematical 5-pillar validation logic.
- `app/dataset.py`: FAISS vector retrieval and embedding management.
- `app/services/personal_records.py`: Local OCR, TF-IDF test classification, and regex metric parsing.
- `frontend/src/App.jsx`: Complete UI state and REST API integrations.

---

# SECTION 15: REVISION NOTES & CHEAT SHEET

- **Name:** Satarka (v3.0.0)
- **Stack:** Python FastAPI + React/Vite + SQLite + FAISS
- **Core Vector Model:** `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- **Symptom Transformer:** `microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext`
- **Fine-Tuning Base Model:** `Qwen/Qwen2.5-0.5B-Instruct` (BitsAndBytes 4-bit NF4 + LoRA)
- **Privacy Standard:** 100% offline local PDF/Image OCR processing.
