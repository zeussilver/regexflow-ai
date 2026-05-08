# Phase 1 + 2 Manual Verification Checklist

## 15. Manual Verification Checklist

### Backend

- [ ] GET /api/health/ returns 200.
- [ ] Upload valid .csv returns preview.
- [ ] Upload valid .xlsx returns preview.
- [ ] Upload .txt returns structured 400 error.
- [ ] Upload empty file returns structured 400 error.
- [ ] Backend does not crash on malformed file.
- [ ] Uploaded files are saved under media/uploads/.

### Frontend

- [ ] Frontend loads successfully.
- [ ] File input accepts .csv and .xlsx.
- [ ] Upload button works.
- [ ] Loading state appears.
- [ ] Preview table renders columns and rows correctly.
- [ ] Error message appears for invalid upload.
- [ ] Frontend does not crash if backend returns an error.

### Integration

- [ ] React can call Django API.
- [ ] CORS works locally.
- [ ] CSV preview works end-to-end.
- [ ] XLSX preview works end-to-end.

## 16. Acceptance Criteria

Phase 1 + 2 is complete only when all criteria below are satisfied.

### Functional Criteria

- [ ] Backend project runs locally.
- [ ] Frontend project runs locally.
- [ ] /api/health/ works.
- [ ] /api/files/upload/ works for CSV.
- [ ] /api/files/upload/ works for XLSX.
- [ ] Frontend displays uploaded table preview.
- [ ] Backend returns consistent error format.
- [ ] Frontend displays user-friendly errors.

### Code Quality Criteria

- [ ] Backend logic is separated into views, serializers, and services.
- [ ] No LLM code exists in this phase.
- [ ] No regex replacement code exists in this phase.
- [ ] No large unrelated dependencies are introduced.
- [ ] No API keys or secrets are committed.
- [ ] .env.example exists.
- [ ] .gitignore excludes virtualenv, node_modules, media uploads, and .env.

### Test Criteria

- [ ] Backend tests cover health check.
- [ ] Backend tests cover valid CSV upload.
- [ ] Backend tests cover valid Excel upload.
- [ ] Backend tests cover unsupported file type.
- [ ] Backend tests cover missing file.
- [ ] Backend tests cover empty file.
