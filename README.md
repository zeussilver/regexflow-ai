# RegexFlow AI

## Overview

RegexFlow AI is a Django + React web app for applying AI-assisted, validated text transformations to uploaded tabular data. Users can upload a CSV or XLSX file, preview the table, ask for a regex in natural language, review the generated Python-compatible pattern, and apply deterministic replacements to a selected column.

The app also includes two optional transformation assistants:

- PII Redaction Assistant for practical redaction of emails, phone numbers, credit cards, and URLs.
- Phone Normalization for converting phone values to formats such as E164, INTERNATIONAL, NATIONAL, or RFC3966.

RegexFlow AI uses the LLM only to propose regex patterns or bounded transformation policies. The backend performs validation and deterministic data rewriting so the LLM does not directly rewrite uploaded table data.

## Live Demo

- Frontend: `TODO: <DEPLOYED_FRONTEND_URL>`
- Backend API: `TODO: <DEPLOYED_BACKEND_URL>/api`

Deployment URLs are placeholders until the final integration lead provides and verifies live deployment links. Local setup remains available for development and fallback testing.

## Demo Video

- Demo video: `TODO: <DEMO_VIDEO_URL>`
- Recording guide: `docs/demo-video-script.md`

Do not replace the placeholder with a public URL unless the final video has been uploaded and verified.

## Features

- CSV and XLSX upload with a 50-row preview.
- Column selection for regex generation and replacement.
- Natural-language regex generation through an OpenAI-compatible LLM provider.
- Backend regex validation before preview or replacement.
- Match preview showing checked rows, matched rows, and example matches.
- Deterministic regex replacement against one selected column.
- Processed table preview and replacement statistics.
- Processed CSV persistence under backend media storage.
- Optional PII redaction across selected columns or all text-like columns.
- Optional phone normalization using `phonenumbers` and a configurable default region.
- Structured API errors for frontend-friendly validation and failure messages.

## Tech Stack

| Layer | Tools |
| --- | --- |
| Backend | Python, Django 4.2, Django REST Framework |
| Data processing | pandas, openpyxl |
| LLM integration | OpenAI-compatible chat completions API |
| Transformations | Python `re`, custom validation, `phonenumbers` |
| Frontend | React 18, TypeScript, Vite, Axios |
| Local orchestration | Optional Docker Compose |

## System Architecture

```text
Browser / React frontend
  |
  | VITE_API_BASE_URL
  v
Django REST API
  |
  +-- File upload service
  |     Stores demo uploads in backend media storage
  |     Parses CSV/XLSX with pandas
  |
  +-- Regex engine
  |     Sends sample values and natural-language prompt to LLM
  |     Validates returned regex with backend rules
  |     Builds match previews and applies deterministic replacements
  |
  +-- Transformation services
        Uses LLM for PII policies and phone-normalization rules
        Applies supported transformations with backend code
        Saves processed CSV outputs
```

The LLM is treated as an assistant for generating bounded instructions. The backend owns file parsing, regex compilation, safety checks, row updates, stats, warnings, and processed-file output.

## Project Structure

```text
regexflow-ai/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── config/
│   └── apps/
│       ├── common/
│       ├── files/
│       ├── regex_engine/
│       └── transformations/
├── frontend/
│   ├── package.json
│   ├── .env.example
│   └── src/
│       ├── api/
│       ├── components/
│       ├── pages/
│       └── types/
├── samples/
│   ├── sample_email_redaction.csv
│   ├── sample_pii_redaction.csv
│   └── sample_phone_normalization.csv
├── docs/
│   ├── manual-test-checklist.md
│   └── demo-video-script.md
├── docker-compose.yml
└── README.md
```

## Sample Datasets

Use the files in `samples/` for local testing and demo recording:

| File | Purpose |
| --- | --- |
| `samples/sample_email_redaction.csv` | Regex generation and replacement demo using the `Email` column. |
| `samples/sample_pii_redaction.csv` | PII redaction demo with email, phone, credit-card, URL, and invalid values. |
| `samples/sample_phone_normalization.csv` | Phone normalization demo using Australian numbers and one invalid value. |

The upload API also supports `.xlsx` files, but the committed sample datasets are CSV files.

## Local Setup

Run the backend and frontend in separate terminal windows.

### Backend Setup

Requires Python 3.9 or newer.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver 8000
```

Backend URL: `http://localhost:8000`

API base URL: `http://localhost:8000/api`

### Frontend Setup

Requires Node.js `^20.19.0` or `>=22.12.0`.

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend URL: `http://localhost:5173`

The frontend expects `VITE_API_BASE_URL=http://localhost:8000/api`.

## Environment Variables

Do not commit real API keys, provider tokens, private keys, or production secrets.

### Backend

Create `backend/.env` from `backend/.env.example`.

| Variable | Example | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | `replace-this-secret` | Django secret key. Use a strong generated value for any deployed backend. |
| `DJANGO_DEBUG` | `False` | Keep `False` in production. Local development can set `True` when needed. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,your-backend-domain.com` | Comma-separated allowed hostnames. Add the deployed backend host. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,https://your-frontend-domain.vercel.app` | Comma-separated frontend origins allowed by Django CORS. Add the deployed frontend origin. |
| `LLM_PROVIDER` | `openai_compatible` | LLM provider mode. This app currently supports the OpenAI-compatible provider path. |
| `LLM_API_KEY` | `your_api_key_here` | API key for the configured LLM provider. Placeholder values intentionally fail. |
| `LLM_BASE_URL` | `https://api.example.com/v1` | Base URL for the OpenAI-compatible API. |
| `LLM_MODEL` | `your-model-name` | Chat model name used for regex, PII policy, and phone rule generation. |
| `LLM_TIMEOUT_SECONDS` | `20` | HTTP timeout for LLM requests. |
| `MAX_UPLOAD_SIZE_MB` | `5` | Upload size limit used by deployment configuration and documentation. |
| `PREVIEW_ROW_LIMIT` | `50` | Preview row limit used by deployment configuration and documentation. |
| `DATABASE_URL` | `postgresql://user:password@host:port/dbname` | Optional PostgreSQL connection string. If omitted, local SQLite is used. |

If `LLM_API_KEY`, `LLM_BASE_URL`, or `LLM_MODEL` is missing or still set to a placeholder, LLM-backed endpoints return `LLM_CONFIG_MISSING`.

### Frontend

Create `frontend/.env` from `frontend/.env.example`.

| Variable | Example | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://localhost:8000/api` | Base URL used by Axios clients for backend requests. |

## API Documentation

All API error responses use this shape:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message"
  }
}
```

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/health/` | Returns service health. |
| `POST` | `/api/files/upload/` | Uploads a CSV or XLSX file and returns columns plus preview rows. |
| `POST` | `/api/regex/generate/` | Generates and validates a regex from natural language for one column. |
| `POST` | `/api/regex/replace/` | Applies a validated regex replacement to one column and returns processed preview and stats. |
| `POST` | `/api/transformations/pii-redact/` | Applies practical PII redaction using a bounded LLM-generated policy and backend redaction logic. |
| `POST` | `/api/transformations/phone-normalize/` | Normalizes phone numbers using a bounded LLM-generated rule and `phonenumbers`. |

### Health Check

`GET /api/health/`

Response:

```json
{
  "status": "ok"
}
```

### File Upload

`POST /api/files/upload/`

Request type: `multipart/form-data`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `file` | file | Yes | Supported extensions are `.csv` and `.xlsx`. |

Successful response:

```json
{
  "file_id": "uuid-string",
  "filename": "sample_email_redaction.csv",
  "columns": ["ID", "Name", "Email", "Department", "Notes"],
  "row_count": 4,
  "preview_rows": [
    {
      "ID": 1,
      "Name": "John Doe",
      "Email": "john.doe@example.com",
      "Department": "Sales",
      "Notes": "Primary contact for renewal"
    }
  ]
}
```

### Regex Generation

`POST /api/regex/generate/`

Request:

```json
{
  "file_id": "uuid-string",
  "target_column": "Email",
  "natural_language": "Find email addresses"
}
```

Successful response:

```json
{
  "regex": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b",
  "flags": [],
  "explanation": "Matches common email addresses.",
  "target_column": "Email",
  "match_preview": {
    "checked_rows": 4,
    "matched_rows": 4,
    "examples": [
      {
        "row_index": 0,
        "value": "john.doe@example.com",
        "matches": ["john.doe@example.com"]
      }
    ]
  },
  "warnings": []
}
```

### Regex Replacement

`POST /api/regex/replace/`

Request:

```json
{
  "file_id": "uuid-string",
  "target_column": "Email",
  "regex": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b",
  "flags": [],
  "replacement": "REDACTED"
}
```

Successful response:

```json
{
  "file_id": "uuid-string",
  "processed_file_id": "uuid-string",
  "target_column": "Email",
  "regex": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b",
  "flags": [],
  "replacement": "REDACTED",
  "columns": ["ID", "Name", "Email", "Department", "Notes"],
  "row_count": 4,
  "preview_limit": 50,
  "processed_preview": [
    {
      "ID": 1,
      "Name": "John Doe",
      "Email": "REDACTED",
      "Department": "Sales",
      "Notes": "Primary contact for renewal"
    }
  ],
  "stats": {
    "checked_rows": 4,
    "matched_rows": 4,
    "total_matches": 4,
    "replaced_rows": 4
  },
  "warnings": []
}
```

### PII Redaction

`POST /api/transformations/pii-redact/`

Request:

```json
{
  "file_id": "uuid-string",
  "target_columns": ["Email", "Phone", "Card", "Website"],
  "natural_language": "Redact common sensitive personal information.",
  "pii_types": ["email", "phone", "credit_card", "url"],
  "replacement_strategy": "typed_placeholders"
}
```

Notes:

- `target_columns` is optional. If omitted or empty, the backend redacts all text-like columns.
- Supported `pii_types` are `email`, `phone`, `credit_card`, and `url`.
- Supported `replacement_strategy` values are `typed_placeholders` and `generic_redacted`.

Successful response includes `processed_file_id`, `processed_preview`, `policy`, `stats`, and `warnings`.

### Phone Normalization

`POST /api/transformations/phone-normalize/`

Request:

```json
{
  "file_id": "uuid-string",
  "target_columns": ["Phone"],
  "natural_language": "Normalize phone numbers to international format",
  "default_region": "AU",
  "target_format": "E164"
}
```

Supported `target_format` values are `E164`, `INTERNATIONAL`, `NATIONAL`, and `RFC3966`. The backend validates the default region with `phonenumbers`, preserves invalid values by default, and returns processed preview rows plus `checked_cells`, `normalized_cells`, `invalid_cells`, and `unchanged_cells` stats.

## LLM Usage

RegexFlow AI uses an OpenAI-compatible chat completions API for three bounded tasks:

- Regex generation: the LLM receives the selected column name, a small sample of non-empty values, and the user's natural-language pattern request. It must return JSON containing a regex, explanation, flags, and confidence.
- PII redaction policy: the LLM chooses supported PII types, target-column policy, and replacement strategy. It must not return transformed rows.
- Phone normalization rule: the LLM chooses a supported output format, default region, and invalid-value behavior. It must not return transformed rows.

The LLM does not directly rewrite table data because generated prose or row-level output can be non-deterministic, difficult to audit, and unsafe to apply blindly to user data. Instead, the backend accepts only structured JSON instructions, validates them against supported options, and performs deterministic transformations with Python code. This keeps replacement behavior reproducible, lets the app report exact stats, and ensures regex and transformation rules are checked before they touch uploaded data.

## Safety and Validation

- Uploaded files are parsed by pandas and returned as previews capped at 50 rows.
- Regex patterns are compiled with Python `re` before preview or replacement.
- Regex patterns longer than 300 characters are rejected.
- Only `IGNORECASE` and `MULTILINE` flags are supported; unsupported flags are ignored with warnings.
- Known risky regex shapes are rejected as `REGEX_UNSAFE`.
- Replacement runs in backend code against the selected column, not in the LLM.
- PII redaction supports only known PII detectors and known replacement strategies.
- Credit-card redaction checks candidate numbers with Luhn validation.
- Phone normalization uses `phonenumbers` and preserves invalid values unless the generated or explicit rule says otherwise.
- Structured API errors avoid exposing stack traces to the frontend.

## Testing

Backend tests:

```bash
cd backend
source .venv/bin/activate
python manage.py test
```

Frontend build:

```bash
cd frontend
npm install
npm run build
```

Manual sample-data flow:

1. Start the backend and frontend locally.
2. Upload `samples/sample_email_redaction.csv`.
3. Select `Email`, generate a regex with `Find email addresses`, and apply replacement value `REDACTED`.
4. Upload `samples/sample_pii_redaction.csv`, run PII redaction, and confirm typed placeholders appear in the processed preview.
5. Upload `samples/sample_phone_normalization.csv`, select `Phone`, use default region `AU`, choose `E164`, and confirm valid phone numbers normalize while the invalid value remains readable.
6. Check the stats panels and warnings for each operation.

See `docs/manual-test-checklist.md` and `docs/demo-video-script.md` for the complete manual verification and demo flow.

## Deployment

The repository includes Dockerfiles and `docker-compose.yml` for local containerized runs:

```bash
docker compose up --build
```

Recommended backend deployment settings for Render or Railway:

```text
Root directory: backend
Build command: pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
Start command: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

If the platform does not expose `$PORT`, use:

```text
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

Recommended frontend deployment settings for Vercel:

```text
Root directory: frontend
Build command: npm run build
Output directory: dist
Environment variable:
  VITE_API_BASE_URL=https://your-backend-domain.com/api
```

Deployment-specific values to configure:

- Backend host and CORS origin values.
- Frontend `VITE_API_BASE_URL`.
- Production-safe `DJANGO_SECRET_KEY`.
- LLM provider credentials and model values.
- Persistent storage strategy for uploaded and processed files.

Current deployment placeholders:

- Frontend: `TODO: <DEPLOYED_FRONTEND_URL>`
- Backend API: `TODO: <DEPLOYED_BACKEND_URL>/api`

## Known Limitations

- Large-file streaming is not implemented.
- Uploaded files are intended for demo use.
- File persistence may depend on hosting platform.
- Regex generation depends on configured LLM provider.
- PII detection is practical but not compliance-grade.
- Phone normalization depends on `phonenumbers` and default region.

## Future Improvements

- Add production-grade object storage for uploads and processed outputs.
- Add authentication, authorization, and per-user file isolation.
- Add large-file streaming and background job processing.
- Add richer audit logs for generated rules and applied transformations.
- Expand transformation assistants while keeping deterministic backend execution.
- Add end-to-end browser tests for the complete upload-to-download workflow.
- Add deployment-specific health checks and observability.

## Author

RegexFlow AI was prepared for final project delivery by the Phase 6 team.
