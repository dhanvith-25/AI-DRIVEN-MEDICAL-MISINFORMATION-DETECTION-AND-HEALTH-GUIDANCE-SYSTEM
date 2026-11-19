# AI-Driven Medical Misinformation Detection and Health Guidance System

AI-Driven Medical Misinformation Detection and Health Guidance System is a research prototype for checking health claims and exploring health information. It combines a FastAPI backend, a React/Vite web app, local machine-learning models, a SQLite database, and optional online evidence services.

> **Important:** AI-Driven Medical Misinformation Detection and Health Guidance System is not a medical device and does not provide medical advice, diagnosis, or treatment. Its claim and symptom models use limited research data; do not use their output for health decisions.

## What it does

- Classifies health claims as `SUPPORTED`, `CONTRADICTED`, or `UNCERTAIN`.
- Checks claims against the local verified-claims dataset and can use configured LLM and web-search providers to gather more evidence.
- Scores supporting evidence and records query history in SQLite.
- Assesses symptoms using a local symptom dataset and provides risk information and a disclaimer.
- Accepts PDF and image lab reports, extracts text locally, stores measurements, and provides search, summaries, and questions about saved records.
- Includes dataset review and an optional experimental model-training pipeline.
- Provides a React/Vite interface and interactive API documentation.

## Requirements

- Python 3.10 or later
- Node.js and npm (for the React web app)
- Tesseract OCR on `PATH` to extract text from image reports; PDF text extraction does not require Tesseract

The first backend run may download the `all-MiniLM-L6-v2` sentence-transformer model if it is not already cached. Some features also require internet access and provider API keys.

## Run locally (Windows PowerShell)

Open a terminal in the project root and install the backend dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Start the backend in this terminal on port `8081` (the default expected by the React app):

```powershell
$env:SATARKA_PORT = "8081"
python -m app.main
```

Alternatively, run `.\scripts\run_backend.ps1`, which sets port `8081` and starts the backend.

In a second terminal, install and start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the React app at <http://127.0.0.1:5173/>. The API is at <http://127.0.0.1:8081/> and its interactive docs are at <http://127.0.0.1:8081/docs>. You can also use the simple backend-served page at <http://127.0.0.1:8081/>.

To run the backend directly without setting `SATARKA_PORT`, it listens on port `8000`. If you use that port, set `VITE_API_URL` in the frontend terminal before `npm run dev`:

```powershell
$env:VITE_API_URL = "http://127.0.0.1:8000"
```

## Optional configuration

The backend loads environment variables from a `.env` file in the project root. Create one only if you need external providers; no `.env.example` is included. Add only the keys for services you have configured:

```dotenv
GROQ_API_KEY=
OPENROUTER_API_KEY=
TAVILY_API_KEY=
GOOGLE_FACTCHECK_API_KEY=
```

- Groq and OpenRouter keys enable the configured LLM routes and evidence validation.
- Tavily enables live web search.
- Google Fact Check enables that optional fact-check source.
- Local claim classification, the bundled dataset, and local report processing do not require these keys. Online-backed features may be unavailable without their providers.

The SQLite database defaults to `data/satarka.db`. Personal report files default to `data/personal_reports/`; report uploads are limited to 10 MB by default. These locations and limits can be changed with `SATARKA_DB`, `PERSONAL_REPORTS_DIR`, and `PERSONAL_REPORT_MAX_BYTES`.

## Useful API endpoints

Use `/docs` for request and response schemas for all available endpoints. Common endpoints include:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/status` | Check API status |
| `GET` | `/health` | Check configuration and service status |
| `POST` | `/health/predict` | Classify a claim, e.g. `{"claim":"Antibiotics cure the common cold"}` |
| `POST` | `/health/upload` | Classify claims in a CSV file |
| `POST` | `/query` | Run evidence-based claim verification, e.g. `{"query":"Does vaccination reduce the risk of severe disease?"}` |
| `POST` | `/symptom-check` | Request a symptom assessment |
| `POST` | `/personal-reports/upload` | Upload a PDF or image report using multipart form field `file` |
| `GET` | `/personal-reports/search?q=glucose` | Search saved reports |
| `GET` | `/personal-reports/summary` | Summarize saved measurements |
| `POST` | `/personal-reports/ask` | Ask about saved reports, e.g. `{"question":"How has my blood sugar changed?"}` |
| `GET` | `/training/status` | Check the optional training pipeline |

Image report OCR requires the Tesseract executable installed separately and available on `PATH`. Report files and extracted records are stored locally by default. Treat the database and `data/personal_reports/` as sensitive health data.

## Tests

From the project root, activate the virtual environment and run:

```powershell
pytest -q
```

To verify the frontend build:

```powershell
cd frontend
npm run build
```

The repository includes test results and a more detailed project analysis in `Testing_Results.md` and `Project_Analysis_Report.md`. Recorded test outcomes are prototype test results, not clinical accuracy or evidence of medical reliability.

## Project layout

```text
app/        FastAPI application, services, database, and training pipeline
frontend/   React/Vite web application
data/       Claim and symptom datasets, FAISS index, SQLite database, report storage
models/     Health-claim classifier model
scripts/    Backend and training helper scripts
tests/      API, model, retrieval, report, and validator tests
```

Model training is disabled by default. The optional Qwen/LoRA training pipeline is experimental and may require additional training-specific packages and suitable hardware; enabling `TRAINING_ENABLED` alone does not install those dependencies.
