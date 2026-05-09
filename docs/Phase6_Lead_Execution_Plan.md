# Phase 6 Lead Execution and Acceptance Plan

Project: RegexFlow AI  
Scope: Phase 6 only: final delivery, deployment preparation, README completion, demo-video preparation, and final submission readiness  
Lead role: Codex Lead coordinates, reviews, integrates, validates, and reports. Workers execute bounded scopes in separate branches/worktrees.  

## 1. Objective

Make RegexFlow AI submission-ready without adding new product features.

Phase 6 is complete only when a marker can:

1. Open the GitHub repository.
2. Read a complete README.
3. Open the public frontend deployment.
4. Use the public backend through the frontend.
5. Upload CSV/XLSX files.
6. Generate regex from natural language.
7. Apply regex replacement.
8. Run PII redaction.
9. Run phone normalization.
10. Watch the demo video from the README.
11. Verify no secrets are exposed.

## 2. Non-Goals and Guardrails

Do not implement:

- Authentication.
- New transformations.
- Multi-file batch processing.
- Large-file streaming.
- Major UI redesign.
- Database-heavy workflow changes.
- New LLM providers unless current deployment is broken.
- Unrelated refactoring.

Guardrails:

- No real API keys or secrets in Git, README, screenshots, or demo video.
- No LLM API keys in frontend environment variables.
- LLM output must remain validated by the backend before deterministic execution.
- Do not remove `.env.example`, docs, sample datasets, or tests.
- Do not claim public deployment is verified until public URLs have been tested.

## 3. Current Repo Observations

Observed before execution:

- `docs/Phase6.md` exists and defines final delivery requirements.
- `README.md` is still Phase 4-oriented and must be updated for Phase 5/5.5/6.
- `backend/.env`, `frontend/.env`, `backend/db.sqlite3`, `backend/media/*`, `frontend/dist`, `frontend/node_modules`, `.DS_Store`, and Python caches exist locally and must not be committed.
- `.gitignore` already covers many local artifacts but should be checked against Phase 6 requirements, especially build output and media paths.
- `backend/requirements.txt` is missing production deployment dependencies required by Phase 6, including `gunicorn` and likely `whitenoise`.
- `backend/config/settings.py` reads core environment variables but currently defaults to local-development behavior and lacks production static-file handling.
- `backend/.env.example` uses local defaults and should be changed to assignment-safe production-ready placeholders.
- `frontend/.env.example` already contains `VITE_API_BASE_URL=http://localhost:8000/api`.
- Required sample datasets already exist in `samples/`.

## 4. Team Execution Model

Use the team skill because this phase spans repository hygiene, backend deployment readiness, frontend production readiness, documentation, deployment verification, and final QA. Workstreams are separable, but Lead owns integration and final acceptance.

Integration branch:

```text
codex/phase6-final-delivery
```

Worktree root:

```text
../worktrees
```

Team artifacts root:

```text
artifacts/team/phase6-final-delivery
```

Worker branches:

| Worker | Branch | Scope | Primary Ownership |
|---|---|---|---|
| W1A | `codex-phase6-w1a-repo-hygiene` | Repository cleanup and secret hygiene | `.gitignore`, cleanup inventory, sample dataset verification |
| W1B | `codex-phase6-w1b-backend-prod` | Backend production readiness | `backend/.env.example`, `backend/config/settings.py`, `backend/requirements.txt`, deployment notes if needed |
| W1C | `codex-phase6-w1c-frontend-prod` | Frontend production readiness | `frontend/.env.example`, `frontend/src/api/*`, user-facing error/build checks |
| W1D | `codex-phase6-w1d-readme-demo` | README and demo preparation | `README.md`, demo script/checklist docs |
| W1E | `codex-phase6-w1e-regression-report` | Regression checklist and final report | test logs, manual checklist, final implementation report |

Merge order:

1. W1A repository hygiene.
2. W1B backend production readiness.
3. W1C frontend production readiness.
4. W1D README/demo documentation.
5. W1E regression/reporting.

## 5. Lead Preflight

Lead tasks:

1. Confirm branch and worktree state:

```bash
git status --short
git branch --show-current
git worktree list
```

2. Create integration branch if not already present:

```bash
git checkout -b codex/phase6-final-delivery
mkdir -p artifacts/team/phase6-final-delivery
```

3. Create status board:

```text
artifacts/team/phase6-final-delivery/status_board.md
```

4. Record preflight facts:

```text
artifacts/team/phase6-final-delivery/lead_preflight.md
```

5. Run baseline checks if dependencies are available:

```bash
cd backend && python manage.py test
cd backend && python manage.py check
cd frontend && npm run build
```

6. If baseline fails, record failures. Do not let workers hide pre-existing failures.

Preflight gate:

- Integration branch exists.
- Worker scopes are disjoint.
- Protected files and no-go items are documented.
- Local secrets are identified as local-only.
- Baseline command status is recorded.

## 6. Worker Packets

### W1A: Repository Cleanup and Secret Hygiene

Objective:

Make the repository clean for submission and verify no generated/runtime artifacts or secrets are tracked.

Allowed files:

- `.gitignore`
- `samples/*`
- `artifacts/team/phase6-final-delivery/W1A_final_report.md`

Execution tasks:

1. Verify `.gitignore` excludes:
   - Python caches.
   - Virtual environments.
   - Local env files.
   - `node_modules`.
   - `frontend/dist`.
   - Uploaded media.
   - Processed media.
   - Logs.
   - OS/editor files.
2. Identify any tracked runtime artifacts with:

```bash
git ls-files | grep -E '(^|/)(__pycache__|.*\.pyc$|\.env$|\.env\.local$|node_modules|frontend/dist|backend/media/(uploads|processed)|\.DS_Store|.*\.log$|db\.sqlite3$)' || true
```

3. Verify `samples/` contains:
   - `sample_email_redaction.csv`
   - `sample_pii_redaction.csv`
   - `sample_phone_normalization.csv`
4. Check samples are synthetic and contain no real PII.
5. Do not delete user-local files unless Lead explicitly approves during integration.

Validation:

```bash
git status --short
git ls-files | grep -E '(^|/)(__pycache__|.*\.pyc$|\.env$|\.env\.local$|node_modules|frontend/dist|backend/media/(uploads|processed)|\.DS_Store|.*\.log$|db\.sqlite3$)' || true
```

Acceptance:

- `.gitignore` meets Phase 6 requirements.
- No tracked secrets or generated artifacts remain.
- Required sample datasets are present and synthetic.

### W1B: Backend Production Readiness

Objective:

Prepare Django backend for demo deployment while preserving existing APIs and behavior.

Allowed files:

- `backend/.env.example`
- `backend/config/settings.py`
- `backend/requirements.txt`
- Backend deployment docs/config files only if already appropriate for the repo
- `artifacts/team/phase6-final-delivery/W1B_final_report.md`

Execution tasks:

1. Update `backend/.env.example` to include:

```env
DJANGO_SECRET_KEY=replace-this-secret
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,your-backend-domain.com
CORS_ALLOWED_ORIGINS=http://localhost:5173,https://your-frontend-domain.vercel.app
LLM_PROVIDER=openai_compatible
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=your-model-name
LLM_TIMEOUT_SECONDS=20
MAX_UPLOAD_SIZE_MB=5
PREVIEW_ROW_LIMIT=50
DATABASE_URL=postgresql://user:password@host:port/dbname
```

2. Ensure settings read `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and `CORS_ALLOWED_ORIGINS` from environment.
3. Add production static-file support, preferably `whitenoise`, if not already present.
4. Add optional `DATABASE_URL` support only if it can be done cleanly and with dependencies documented.
5. Ensure missing LLM config still produces structured API errors, not stack traces.
6. Ensure deployment requirements include actual runtime dependencies:
   - Django
   - djangorestframework
   - django-cors-headers
   - pandas
   - openpyxl
   - python-dotenv or equivalent if used
   - requests or current OpenAI-compatible client dependency if used
   - gunicorn
   - whitenoise if configured
   - phonenumbers
   - dj-database-url and psycopg2-binary if `DATABASE_URL` is supported

Validation:

```bash
cd backend
python manage.py test
python manage.py check
python manage.py check --deploy
python manage.py collectstatic --noinput
```

Acceptance:

- Backend can run locally.
- Backend can collect static files.
- `check --deploy` warnings are either fixed or documented as acceptable assignment-demo warnings.
- No production default exposes debug stack traces.
- `/api/health/` remains available.

### W1C: Frontend Production Readiness

Objective:

Ensure the React/Vite frontend builds cleanly and uses deploy-time API configuration consistently.

Allowed files:

- `frontend/.env.example`
- `frontend/src/api/*`
- `frontend/src/components/*` only for friendly error/loading fixes
- `frontend/src/pages/*` only for friendly error/loading fixes
- `frontend/src/types/*` if needed for existing API response consistency
- `artifacts/team/phase6-final-delivery/W1C_final_report.md`

Execution tasks:

1. Verify all API clients use `VITE_API_BASE_URL`.
2. Remove or gate any hardcoded `localhost` outside examples/docs.
3. Confirm no LLM secrets are referenced in frontend env or code.
4. Improve friendly errors only where existing deployment latency/network failures are confusing.
5. Do not redesign the app.

Validation:

```bash
cd frontend
npm install
npm run build
npm run lint
```

If `npm run lint` does not exist, document it as not applicable.

Acceptance:

- `npm run build` passes.
- Frontend can be configured with `VITE_API_BASE_URL=https://your-backend-domain.com/api`.
- No frontend secret variables are introduced.
- No hardcoded local backend URL is used in production code.

### W1D: README and Demo Preparation

Objective:

Make README complete enough for grading and prepare the demo video flow.

Allowed files:

- `README.md`
- `docs/demo-video-script.md` or similar demo checklist doc
- `artifacts/team/phase6-final-delivery/W1D_final_report.md`

Execution tasks:

1. Rewrite README with required sections:
   - Overview
   - Live Demo
   - Demo Video
   - Features
   - Tech Stack
   - System Architecture
   - Project Structure
   - Sample Datasets
   - Local Setup
   - Environment Variables
   - API Documentation
   - LLM Usage
   - Safety and Validation
   - Testing
   - Deployment
   - Known Limitations
   - Future Improvements
   - Author
2. Include API documentation for:
   - `GET /api/health/`
   - `POST /api/files/upload/`
   - `POST /api/regex/generate/`
   - `POST /api/regex/replace/`
   - `POST /api/transformations/pii-redact/`
   - `POST /api/transformations/phone-normalize/`
3. Explain that the LLM generates structured regex/policies/rules but does not directly rewrite table data.
4. Add placeholders for:
   - GitHub repository URL.
   - Public frontend URL.
   - Public backend health-check URL.
   - Demo video URL.
5. Prepare a 2-4 minute demo script using the three sample datasets.
6. Include known limitations exactly aligned with Phase 6.

Validation:

```bash
grep -n "Live Demo\\|Demo Video\\|API Documentation\\|Known Limitations" README.md
grep -n "/api/health/\\|/api/files/upload/\\|/api/regex/generate/\\|/api/regex/replace/\\|/api/transformations/pii-redact/\\|/api/transformations/phone-normalize/" README.md
grep -R "LLM_API_KEY=.*[^_].*" README.md docs || true
```

Acceptance:

- README is complete, accurate, and does not expose secrets.
- Demo flow is clear enough to record without improvising.
- Links are present as placeholders before deployment and replaced after deployment.

### W1E: Regression Checklist and Final Report

Objective:

Run final checks after integration and produce the Phase 6 implementation report.

Allowed files:

- `docs/manual-test-checklist.md`
- `artifacts/team/phase6-final-delivery/*`
- README link placeholders only after public URLs/video exist

Execution tasks:

1. Run local backend checks:

```bash
cd backend
python manage.py test
python manage.py check
python manage.py check --deploy
```

2. Run local frontend checks:

```bash
cd frontend
npm run build
npm run lint
```

3. Run manual local E2E:
   - Upload `sample_email_redaction.csv`.
   - Generate regex: `Find email addresses`.
   - Apply replacement: `REDACTED`.
   - Upload `sample_pii_redaction.csv`.
   - Apply PII redaction for all PII types.
   - Upload `sample_phone_normalization.csv`.
   - Normalize phones to international format with default region `AU`.
4. After public deployment, verify:
   - Backend `/api/health/`.
   - Upload endpoint.
   - Regex generation.
   - Regex replacement.
   - PII redaction.
   - Phone normalization.
   - Frontend public URL loads and can call backend.
5. Produce implementation report with:
   - Repository cleanup completed.
   - Files created or modified.
   - Backend production-readiness changes.
   - Frontend production-readiness changes.
   - Deployment configuration used.
   - Public backend URL.
   - Public frontend URL.
   - README sections completed.
   - Demo video link added.
   - Tests run and results.
   - Known limitations.
   - Deployment warnings.
   - Acceptance criteria status.

Acceptance:

- All test results are recorded honestly.
- Any unavailable deployment/video step is marked blocked with exact reason.
- Final report gives a clear Phase 6 decision.

## 7. Lead Merge and Review Protocol

For each worker:

```bash
git checkout codex/phase6-final-delivery
git status --short
git diff --name-only codex/phase6-final-delivery...<worker-branch>
git diff --stat codex/phase6-final-delivery...<worker-branch>
```

Lead review checks:

- Changed files are within assigned scope.
- No real `.env` values, API keys, tokens, or secrets appear in diff.
- No new features or broad refactors.
- No local runtime artifacts are added.
- Worker report exists and lists commands run.
- Tests pass or failures are documented with exact cause.

Merge command:

```bash
git merge --no-ff <worker-branch> -m "Merge <worker-id> <scope> into codex/phase6-final-delivery"
```

Post-merge minimum checks:

```bash
git status --short
cd backend && python manage.py check
cd frontend && npm run build
```

Record every merge in:

```text
artifacts/team/phase6-final-delivery/lead_merge_log.md
```

## 8. Deployment Execution Plan

### Backend First

Recommended platform: Render or Railway.

Settings:

```text
Root directory: backend
Build command: pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
Start command: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

Required environment variables:

```text
DJANGO_SECRET_KEY=<strong generated secret>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<backend-host>
CORS_ALLOWED_ORIGINS=http://localhost:5173,https://<frontend-host>
LLM_PROVIDER=openai_compatible
LLM_API_KEY=<provider key>
LLM_BASE_URL=<provider base url>
LLM_MODEL=<model name>
LLM_TIMEOUT_SECONDS=20
MAX_UPLOAD_SIZE_MB=5
PREVIEW_ROW_LIMIT=50
```

Backend deployment acceptance:

```bash
curl https://<backend-host>/api/health/
```

Expected:

```json
{"status":"ok"}
```

### Frontend Second

Recommended platform: Vercel.

Settings:

```text
Root directory: frontend
Build command: npm run build
Output directory: dist
Environment variable:
  VITE_API_BASE_URL=https://<backend-host>/api
```

Frontend deployment acceptance:

- Public URL loads.
- Browser network calls target the deployed backend.
- No CORS or allowed-host errors.

## 9. Demo Video Execution Plan

Target length: 2-4 minutes.

Script:

1. Open deployed frontend.
2. Introduce RegexFlow AI briefly.
3. Upload `samples/sample_email_redaction.csv`.
4. Show original preview.
5. Select Email column.
6. Enter `Find email addresses`.
7. Generate regex.
8. Show regex and match preview.
9. Enter replacement `REDACTED`.
10. Apply replacement.
11. Show processed table and stats.
12. Upload `samples/sample_pii_redaction.csv`.
13. Open PII Redaction Assistant.
14. Select all PII types.
15. Apply redaction.
16. Show redacted result and stats.
17. Upload `samples/sample_phone_normalization.csv`.
18. Open Phone Normalization.
19. Enter `Normalize phone numbers to international format`.
20. Set default region `AU`.
21. Apply normalization.
22. Show normalized result and invalid value handling.
23. Show README with live demo and backend links.

Before recording:

- Backend is deployed and awake.
- Frontend is deployed.
- LLM API key is configured in backend only.
- Browser does not show secrets.
- No local `.env` tabs or provider dashboards are visible.
- No stack traces are visible.

## 10. Final Acceptance Matrix

| Area | Acceptance Criteria | Evidence |
|---|---|---|
| Repository | No committed `.env`, API keys, caches, media uploads, `node_modules`, or build output | `git ls-files` secret/artifact scan |
| README | All required sections present and accurate | README review |
| Backend local | Tests and Django checks pass | `python manage.py test`, `python manage.py check` |
| Backend deploy | Public `/api/health/` returns `{"status":"ok"}` | Public URL/curl result |
| Frontend local | Production build passes | `npm run build` |
| Frontend deploy | Public URL loads and calls backend | Browser/manual E2E |
| Regex flow | Upload, generate, preview, replace, stats work | Manual E2E |
| PII flow | Redaction works on synthetic sample | Manual E2E |
| Phone flow | AU normalization and invalid handling work | Manual E2E |
| Security | Secrets only in backend deploy env, not Git/README/video | Secret scan and demo review |
| Demo | Demo video linked in README | README link |

## 11. Final Report Template

Lead will produce:

```text
artifacts/team/phase6-final-delivery/phase6-final-delivery_summary.md
```

Required contents:

1. Repository cleanup completed.
2. Files created or modified.
3. Backend production-readiness changes.
4. Frontend production-readiness changes.
5. Deployment configuration used.
6. Public backend URL.
7. Public frontend URL.
8. README sections completed.
9. Demo video link added.
10. Tests run and results.
11. Known limitations.
12. Deployment warnings.
13. Phase 6 acceptance criteria status.

Decision labels:

- `SUBMISSION_READY`: all acceptance criteria complete.
- `READY_EXCEPT_EXTERNAL_DEPLOYMENT`: code/docs ready, but public deployment/video needs user credentials or manual upload.
- `NEEDS_MORE_REVIEW`: tests or deployment checks failed and require another pass.
- `DO_NOT_SUBMIT`: secrets, broken core flow, or missing README/demo blockers remain.

## 12. Lead Closeout

After all approved worker branches are merged:

1. Run final local validation:

```bash
cd backend && python manage.py test
cd backend && python manage.py check
cd backend && python manage.py check --deploy
cd frontend && npm run build
```

2. Verify no prohibited tracked artifacts:

```bash
git ls-files | grep -E '(^|/)(__pycache__|.*\.pyc$|\.env$|\.env\.local$|node_modules|frontend/dist|backend/media/(uploads|processed)|\.DS_Store|.*\.log$|db\.sqlite3$)' || true
```

3. Verify no obvious placeholder secrets:

```bash
git grep -nE '(sk-[A-Za-z0-9]|api[_-]?key\\s*=\\s*[^< ]|BEGIN [A-Z ]*PRIVATE KEY)' -- . ':!docs/Phase6_Lead_Execution_Plan.md' || true
```

4. Update README with real public URLs and demo video link after deployment/video are complete.
5. Remove completed worker worktrees or record why any are retained.
6. Produce the final summary and implementation report.
