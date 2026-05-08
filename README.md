# RegexFlow AI

RegexFlow AI is a Django + React application for uploading CSV or Excel files and previewing tabular data. This repository currently implements Phase 1 + Phase 2 only: project foundations, health checks, file upload, pandas parsing, and table preview.

Out of scope for this phase: LLM integration, regex generation, regex replacement, processed-file download, authentication, deployment, large-file streaming, and complex database models.

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
│       └── files/
├── frontend/
│   ├── package.json
│   └── src/
│       ├── api/
│       ├── components/
│       ├── pages/
│       └── types/
├── docs/
│   └── Phase_1+2.md
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

## Local Docker Compose

`docker-compose.yml` is included as a local convenience target. The standard development flow above is preferred for Phase 1 + 2.

```bash
docker compose up --build
```

## Phase Status

Phase 1 + 2 includes local Django and React foundations, health-check API, CSV/XLSX upload API, pandas parsing, frontend upload UI, preview table, and local integration.
