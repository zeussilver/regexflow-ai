# RegexFlow AI

RegexFlow AI is a Django + React application for uploading CSV or Excel files, previewing tabular data, generating Python-compatible regex patterns from natural language, and applying deterministic replacements to selected text columns.

This repository currently implements Phase 1 through Phase 4: project foundations, health checks, file upload, pandas parsing, table preview, LLM regex generation, backend regex validation, match preview, replacement execution, processed CSV saving, replacement statistics, and processed-data preview.

Out of scope until later phases: processed-file download UI/API, authentication, deployment, multi-column replacement, large-file streaming, and optional extra data transformations.

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
│       └── regex_engine/
├── frontend/
│   ├── package.json
│   └── src/
│       ├── api/
│       ├── components/
│       ├── pages/
│       └── types/
├── docs/
│   ├── Phase_1+2.md
│   ├── Phase3.md
│   └── Phase4.md
├── AGENT.md
├── README.md
├── .gitignore
└── docker-compose.yml
```

## Backend Setup

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

### LLM Configuration

Phase 3 uses an OpenAI-compatible chat completions API. Add these values to `backend/.env`:

```env
LLM_PROVIDER=openai_compatible
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=your-model-name
LLM_TIMEOUT_SECONDS=20
```

Do not commit real API keys. If `LLM_API_KEY`, `LLM_BASE_URL`, or `LLM_MODEL` is missing, `POST /api/regex/generate/` returns a structured `LLM_CONFIG_MISSING` error.

Run backend tests:

```bash
cd backend
source .venv/bin/activate
python manage.py test
```

## Frontend Setup

Requires Node.js `^20.19.0` or `>=22.12.0`.

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend URL: `http://localhost:5173`

The frontend expects `VITE_API_BASE_URL=http://localhost:8000/api`.
For local development, the backend allows local browser origins through CORS while `DJANGO_DEBUG=1`.

## API Endpoints

### `GET /api/health/`

Returns service health.

### `POST /api/files/upload/`

Multipart form upload field: `file`

Supported file types:

- `.csv`
- `.xlsx`

Constraints:

- Maximum upload size: 5 MB
- Preview rows returned: 50

Successful response:

```json
{
  "file_id": "uuid",
  "filename": "example.csv",
  "columns": ["Name", "Email"],
  "row_count": 2,
  "preview_rows": [
    { "Name": "Ada", "Email": "ada@example.com" }
  ]
}
```

Structured error response:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message"
  }
}
```

### `POST /api/regex/generate/`

Generates a regex for one uploaded file column using natural language, validates the regex, and returns a match preview from the first 50 rows.

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
  "regex": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,7}\\b",
  "flags": [],
  "explanation": "Matches common email addresses.",
  "target_column": "Email",
  "match_preview": {
    "checked_rows": 50,
    "matched_rows": 3,
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

Regex generation errors use the same structured error shape. Phase 3 handles `FILE_NOT_FOUND`, `COLUMN_NOT_FOUND`, `EMPTY_NATURAL_LANGUAGE`, `LLM_CONFIG_MISSING`, `LLM_API_ERROR`, `LLM_INVALID_JSON`, `REGEX_MISSING`, `REGEX_TOO_LONG`, `REGEX_COMPILE_ERROR`, `REGEX_UNSAFE`, and `INTERNAL_ERROR`.

### `POST /api/regex/replace/`

Applies a validated regex to one selected column, saves the full processed CSV under local media storage, and returns a processed preview plus full-file replacement statistics.

Request:

```json
{
  "file_id": "uuid-string",
  "target_column": "Email",
  "regex": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,7}\\b",
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
  "regex": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,7}\\b",
  "flags": [],
  "replacement": "REDACTED",
  "columns": ["Name", "Email"],
  "row_count": 2,
  "preview_limit": 50,
  "processed_preview": [
    { "Name": "Ada", "Email": "REDACTED" }
  ],
  "stats": {
    "checked_rows": 2,
    "matched_rows": 2,
    "total_matches": 2,
    "replaced_rows": 2
  },
  "warnings": []
}
```

Replacement errors use the same structured error shape. Phase 4 handles `FILE_NOT_FOUND`, `COLUMN_NOT_FOUND`, `EMPTY_REGEX`, `MISSING_REPLACEMENT`, `REGEX_TOO_LONG`, `REGEX_COMPILE_ERROR`, `REGEX_UNSAFE`, `FILE_PARSE_ERROR`, `REGEX_REPLACEMENT_ERROR`, and `INTERNAL_ERROR`. A valid regex with no matches returns `200` with zero counts and a warning.

## Local Docker Compose

`docker-compose.yml` is included as a local convenience target. The standard development flow above is preferred for local Phase 4 work.

```bash
docker compose up --build
```

## Phase Status

Phase 1 + 2 includes local Django and React foundations, health-check API, CSV/XLSX upload API, pandas parsing, frontend upload UI, preview table, and local integration.

Phase 3 adds the dedicated Django `regex_engine` app, `POST /api/regex/generate/`, an OpenAI-compatible LLM service, structured LLM JSON parsing, regex safety validation, 50-row match preview, frontend column selection, natural-language regex generation UI, and result preview.

Phase 4 adds `POST /api/regex/replace/`, deterministic full-file replacement for one selected column, processed CSV persistence, replacement value input, processed data preview, replacement warnings, and checked/matched/total/replaced counts.

Phase 5 is the next phase for processed-file download, final polish, README refinements, and demo packaging.
