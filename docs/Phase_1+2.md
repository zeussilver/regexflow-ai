# Phase 1 + 2 Implementation Notes

## Scope

This phase implements the local application foundation and file upload preview workflow.

Included:

- Django backend foundation
- Django REST Framework API setup
- CORS support for the local Vite frontend
- SQLite local database configuration
- Health-check endpoint
- CSV/XLSX upload endpoint
- pandas-based parsing
- 50-row preview response
- React + TypeScript + Vite frontend foundation
- Axios API client
- File upload UI
- Data preview table
- User-friendly error display
- Backend tests for core upload behavior

Excluded:

- LLM integration
- Natural-language regex generation
- Regex replacement
- Processed-file download
- Authentication
- Deployment
- Large-file streaming
- Complex database models

## API Contract

### Health Check

`GET /api/health/`

Expected response:

```json
{
  "status": "ok"
}
```

### File Upload

`POST /api/files/upload/`

Upload field: `file`

Supported extensions:

- `.csv`
- `.xlsx`

Maximum file size: 5 MB

Preview limit: 50 rows

Successful response fields:

- `file_id`
- `filename`
- `columns`
- `row_count`
- `preview_rows`

Structured error shape:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message"
  }
}
```

Required backend error codes:

- `NO_FILE_UPLOADED`
- `UNSUPPORTED_FILE_TYPE`
- `FILE_TOO_LARGE`
- `EMPTY_FILE`
- `FILE_PARSE_ERROR`
- `INTERNAL_ERROR`

## Local Integration

Run the backend at:

```text
http://localhost:8000
```

Run the frontend at:

```text
http://localhost:5173
```

Frontend API base URL:

```text
http://localhost:8000/api
```
