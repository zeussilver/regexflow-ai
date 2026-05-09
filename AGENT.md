# RegexFlow AI Agent Notes

## Current Delivery State

Phase 6 final delivery is implemented. The application is deployed with:

- Frontend: `https://frontend-gamma-gold-32.vercel.app`
- Backend API: `https://regexflow-ai-backend.onrender.com/api`
- Production branch: `codex/phase6-final-delivery`
- Latest verified frontend production deployment: `dpl_JVHtXQcHppFT6XnbyFLC25ckyfpr`
- Latest verified frontend commit: `4f3da89` (`Remove phase labels from frontend`)

The application supports:

- CSV/XLSX upload and 50-row preview.
- Column selection from uploaded file metadata.
- Natural-language regex generation through `POST /api/regex/generate/`.
- OpenAI-compatible LLM calls through `backend/apps/regex_engine/llm_service.py`.
- Structured LLM JSON parsing before regex use.
- Regex length, syntax, and basic safety validation.
- Match preview against the first 50 rows of the selected column.
- Replacement value input after regex generation.
- Deterministic replacement through `POST /api/regex/replace/`.
- Full-file replacement statistics with a 50-row processed preview.
- Processed CSV persistence under `backend/media/processed/{processed_file_id}.csv`.
- Processed CSV download through `GET /api/files/processed/{processed_file_id}/download/`.
- PII redaction through `POST /api/transformations/pii-redact/`.
- Phone normalization through `POST /api/transformations/phone-normalize/`.
- Production-ready Vercel frontend and Render backend configuration.

## Scope Boundaries

Do not add these without an explicit new task:

- User authentication.
- Multi-column replacement.
- Large-file streaming.
- Production object storage for uploads or processed files.
- Compliance-grade PII detection claims.
- Background job processing.

## Existing Architecture

Backend:

- Upload files are saved under `backend/media/uploads/{file_id}.csv` or `{file_id}.xlsx`.
- Processed files are saved under `backend/media/processed/{processed_file_id}.csv`.
- There is no uploaded-file database model; regex workflows reuse deterministic file lookup in `apps.files.services.resolve_uploaded_file`.
- Structured API errors use `apps.common.responses.error_response`.
- Regex generation, match preview, and replacement modules live in `backend/apps/regex_engine/`.
- Optional transformation policy, redaction, normalization, stats, and service modules live in `backend/apps/transformations/`.
- File upload and processed-file download routes live in `backend/apps/files/`.

Frontend:

- Upload, regex generation, replacement, and optional transformation state are coordinated in `frontend/src/pages/HomePage.tsx`.
- Regex API types are in `frontend/src/types/regex.ts`.
- Regex API client is in `frontend/src/api/regex.ts`.
- Transformation API types are in `frontend/src/types/transformations.ts`.
- Transformation API client is in `frontend/src/api/transformations.ts`.
- Core UI components are in `frontend/src/components/`.

Deployment:

- Vercel project root is `frontend/`.
- Vercel build command is `npm run build`.
- Vercel output directory is `dist`.
- Vercel production env should set `VITE_API_BASE_URL=https://regexflow-ai-backend.onrender.com/api`.
- Render backend root is `backend/`.
- Render start command should run `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`.

## Verification Commands

Backend:

```bash
cd backend
source .venv/bin/activate
python manage.py test
python manage.py check
```

Frontend:

```bash
cd frontend
npm run build
```

Deployment smoke checks:

```bash
curl https://regexflow-ai-backend.onrender.com/api/health/
curl -I https://frontend-gamma-gold-32.vercel.app
```

## Environment

Add real local LLM settings to `backend/.env`; never commit secrets:

```env
LLM_PROVIDER=openai_compatible
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=your-model-name
LLM_TIMEOUT_SECONDS=20
```
