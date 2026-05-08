# RegexFlow AI Agent Notes

## Current Phase

Phase 4 is implemented. The application supports:

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

## Scope Boundaries

Do not implement these until Phase 5 or later:

- Processed file download.
- User authentication.
- Deployment.
- Multi-column replacement.
- Large-file streaming.

## Existing Architecture

Backend:

- Upload files are saved under `backend/media/uploads/{file_id}.csv` or `{file_id}.xlsx`.
- Processed files are saved under `backend/media/processed/{processed_file_id}.csv`.
- There is no uploaded-file database model; regex workflows reuse deterministic file lookup in `apps.files.services.resolve_uploaded_file`.
- Structured API errors use `apps.common.responses.error_response`.
- Regex generation, match preview, and replacement modules live in `backend/apps/regex_engine/`.

Frontend:

- Upload, regex generation, and replacement state are coordinated in `frontend/src/pages/HomePage.tsx`.
- Regex API types are in `frontend/src/types/regex.ts`.
- Regex API client is in `frontend/src/api/regex.ts`.
- Regex UI components are in `frontend/src/components/ColumnSelector.tsx`, `RegexGenerationPanel.tsx`, `RegexPreviewCard.tsx`, `ReplacementPanel.tsx`, `ReplacementStatsCard.tsx`, and `ProcessedDataTable.tsx`.

## Verification Commands

Backend:

```bash
cd backend
source .venv/bin/activate
python manage.py test
```

Frontend:

```bash
cd frontend
npm run build
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
