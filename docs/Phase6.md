可以。Phase 6 的目标不是再加功能，而是把项目变成**可提交、可部署、可演示**的最终版本。原文档交付物明确要求：完整 GitHub source code、详细 README、公开可访问 deployment URL、以及嵌入 GitHub README 的 demo video。

部署侧建议后端用 **Railway / Render**，前端用 **Vercel**。Vercel 官方支持 Vite 项目部署，并通过环境变量配置前端构建变量；Railway 官方 Django guide 也强调需要连接 GitHub repo、配置变量并部署 Django 服务。Django 官方部署文档还建议上线前跑 deployment checklist，确保生产环境配置正确。([Vercel][1])

下面是可直接放入仓库的 `docs/Phase_6_Final_Delivery.md`。

````markdown
# Phase 6 Plan: Final Delivery, Deployment, README, and Demo Video

Project: RegexFlow AI  
Scope: Final delivery only  
Status: Planned  
Owner: Codex Lead  
Depends on: Phase 1 + 2 + 3 + 4 + 5 + 5.5 completed

---

## 1. Objective

Phase 6 converts the project from a locally working application into a complete submission-ready product.

By the end of Phase 6, the project must have:

1. A clean GitHub repository.
2. A complete README.md.
3. Publicly accessible frontend deployment URL.
4. Publicly accessible backend API deployment URL.
5. End-to-end deployed functionality.
6. Demo video embedded or linked in the README.
7. No exposed secrets.
8. Final regression tests completed.

This phase is about delivery, not feature expansion.

---

## 2. Assignment Requirements Covered

This phase directly covers the remaining assignment deliverables:

1. Source code submitted through GitHub.
2. Detailed README.md.
3. Public deployment URL.
4. Demo video embedded in GitHub README.
5. Final application can be tested end-to-end.

---

## 3. Non-Goals

Do not implement new product features in Phase 6.

Do not add:

1. New transformation types.
2. Authentication.
3. User accounts.
4. Role-based permissions.
5. Large-file streaming architecture.
6. New database-heavy workflows.
7. Multi-file batch processing.
8. Major UI redesign.
9. New LLM providers unless current provider is broken.
10. Complex CI/CD pipelines beyond basic deployment needs.

Phase 6 is about stabilizing and delivering what already exists.

---

## 4. Feature Freeze

Before starting Phase 6, freeze the feature set.

Final supported features:

1. CSV/XLSX upload.
2. Original table preview.
3. Natural language to regex generation.
4. Regex validation.
5. Match preview.
6. Regex replacement.
7. Processed table display.
8. PII Redaction Assistant.
9. Phone Normalization.
10. Transformation stats.
11. Friendly error handling.
12. Sample datasets.

No extra feature should be added unless it fixes a blocking issue.

---

## 5. Final Delivery Architecture

Recommended deployment architecture:

```text
User Browser
    |
    v
Vercel Frontend
    |
    | HTTPS API requests
    v
Railway / Render Django Backend
    |
    | LLM API call
    v
LLM Provider

Django Backend
    |
    | uploaded and processed files
    v
Temporary media storage
````

Recommended platform split:

| Component             | Recommended Platform                                      |
| --------------------- | --------------------------------------------------------- |
| React + Vite frontend | Vercel                                                    |
| Django backend        | Railway or Render                                         |
| Database              | SQLite for demo only, or PostgreSQL if already configured |
| Uploaded files        | Local/media storage for demo only                         |
| LLM API key           | Backend environment variable                              |

For this assignment, persistent production-grade file storage is not required unless already implemented.

---

## 6. Repository Readiness

### 6.1 Required Top-Level Structure

Final repository should look similar to:

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
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── .env.example
│   └── src/
│
├── docs/
│   ├── Phase_1+2.md
│   ├── Phase_3_LLM_Regex_Generation.md
│   ├── Phase_4_Regex_Replacement.md
│   ├── Phase_5_Optional_Transformations.md
│   ├── Phase_5.5_Requirement_Alignment_Hardening.md
│   └── Phase_6_Final_Delivery.md
│
├── samples/
│   ├── sample_email_redaction.csv
│   ├── sample_pii_redaction.csv
│   └── sample_phone_normalization.csv
│
├── README.md
├── .gitignore
└── LICENSE
```

---

## 7. Final Code Cleanup

### 7.1 Remove Unnecessary Files

Remove:

```text
__pycache__/
*.pyc
.env
.env.local
node_modules/
dist/
media/uploads/*
media/processed/*
.DS_Store
debug logs
temporary notebooks
unused screenshots
local database backups
```

Do not remove:

```text
.env.example
sample files
docs
tests
```

---

### 7.2 Check `.gitignore`

Minimum `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/
env/
*.sqlite3

# Django media
backend/media/uploads/
backend/media/processed/

# Environment
.env
.env.local
.env.production

# Node
node_modules/
frontend/dist/

# OS
.DS_Store

# Logs
*.log
```

---

## 8. Backend Production Readiness

### 8.1 Required Backend Environment Variables

Backend `.env.example` should include:

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
```

If using PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@host:port/dbname
```

---

### 8.2 Django Settings Checklist

Ensure production settings support:

```text
DEBUG=False
SECRET_KEY from environment
ALLOWED_HOSTS from environment
CORS_ALLOWED_ORIGINS from environment
static files configured
media upload path configured
structured error responses
LLM config missing handled gracefully
```

Recommended command before deployment:

```bash
python manage.py check --deploy
```

Warnings can be documented if acceptable for the assignment demo, but security-critical issues should be fixed.

---

### 8.3 Backend Dependencies

`backend/requirements.txt` should include all used packages, for example:

```text
Django
djangorestframework
django-cors-headers
pandas
openpyxl
python-dotenv
requests
gunicorn
whitenoise
phonenumbers
```

If using PostgreSQL:

```text
dj-database-url
psycopg2-binary
```

---

### 8.4 Backend Start Command

Recommended production start command:

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

If the deployment platform requires a fixed default:

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

---

### 8.5 Backend Build Command

Recommended build command:

```bash
pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
```

If database migrations are not used, still run:

```bash
python manage.py collectstatic --noinput
```

---

## 9. Frontend Production Readiness

### 9.1 Frontend Environment Variables

`frontend/.env.example`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

Production Vercel environment variable:

```env
VITE_API_BASE_URL=https://your-backend-domain.com/api
```

Important:

```text
Vite frontend environment variables exposed to client code must use the VITE_ prefix.
Do not put secret API keys in frontend environment variables.
```

---

### 9.2 Frontend Build Verification

Run locally:

```bash
cd frontend
npm install
npm run build
npm run preview
```

Fix all TypeScript and build errors before deployment.

---

### 9.3 Frontend Deployment Settings

Recommended Vercel settings:

```text
Framework Preset: Vite
Root Directory: frontend
Build Command: npm run build
Output Directory: dist
Environment Variable:
  VITE_API_BASE_URL=https://your-backend-domain.com/api
```

---

## 10. CORS and API Connectivity

After deployment, verify:

```text
Frontend deployed domain can call backend deployed domain.
Backend CORS allows frontend URL.
Backend ALLOWED_HOSTS includes backend deployment host.
Frontend VITE_API_BASE_URL points to backend /api root.
```

Common failure cases:

| Problem                        | Likely Cause                             |
| ------------------------------ | ---------------------------------------- |
| Frontend shows network error   | wrong `VITE_API_BASE_URL`                |
| Browser blocks request         | CORS not configured                      |
| Backend returns 400 host error | `ALLOWED_HOSTS` missing deployed domain  |
| LLM fails only in deployment   | missing backend `LLM_API_KEY`            |
| Upload fails                   | platform file size or temp storage issue |

---

## 11. Final Regression Test Plan

Run local tests before deployment.

### 11.1 Backend Tests

```bash
cd backend
python manage.py test
```

Minimum expected coverage:

```text
[ ] health check
[ ] CSV upload
[ ] XLSX upload
[ ] invalid file type
[ ] empty file
[ ] natural language regex generation with mocked LLM
[ ] invalid LLM JSON
[ ] regex validation
[ ] regex replacement
[ ] PII redaction
[ ] phone normalization with mocked LLM rule
[ ] error response format
```

---

### 11.2 Frontend Build Test

```bash
cd frontend
npm install
npm run build
```

If linting exists:

```bash
npm run lint
```

---

### 11.3 Manual Local E2E Test

Use sample datasets and verify:

```text
[ ] Upload sample_email_redaction.csv
[ ] Generate regex: Find email addresses
[ ] Apply replacement: REDACTED
[ ] Processed table shows redacted emails

[ ] Upload sample_pii_redaction.csv
[ ] Apply PII Redaction Assistant
[ ] Emails, phones, URLs, and card-like numbers are redacted

[ ] Upload sample_phone_normalization.csv
[ ] Normalize phone numbers to international format
[ ] Valid AU numbers become E.164 format
[ ] Invalid numbers remain unchanged
```

---

## 12. Deployment Plan

### 12.1 Backend Deployment

Recommended options:

```text
Option A: Railway
Option B: Render
```

Use whichever works fastest with the current repository.

Required backend deployment settings:

```text
Root directory: backend
Build command: pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
Start command: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
Environment variables: from backend/.env.example
```

After backend deploys, verify:

```text
GET https://your-backend-domain.com/api/health/
```

Expected response:

```json
{
  "status": "ok"
}
```

---

### 12.2 Frontend Deployment

Recommended platform:

```text
Vercel
```

Required frontend deployment settings:

```text
Root directory: frontend
Build command: npm run build
Output directory: dist
Environment variable:
  VITE_API_BASE_URL=https://your-backend-domain.com/api
```

After frontend deploys, verify:

```text
Open https://your-frontend-domain.vercel.app
Upload CSV
Generate regex
Apply replacement
Run optional transformations
```

---

## 13. README.md Requirements

Final README should be clear enough that a marker can:

1. Understand what the app does.
2. Run it locally.
3. Configure environment variables.
4. Test the deployed version.
5. Watch the demo video.
6. Review architecture and API design.

Recommended README structure:

```markdown
# RegexFlow AI

## Overview

## Live Demo

## Demo Video

## Features

## Tech Stack

## System Architecture

## Project Structure

## Sample Datasets

## Local Setup

### Backend Setup

### Frontend Setup

## Environment Variables

### Backend

### Frontend

## API Documentation

### Health Check

### File Upload

### Regex Generation

### Regex Replacement

### PII Redaction

### Phone Normalization

## LLM Usage

## Safety and Validation

## Testing

## Deployment

## Known Limitations

## Future Improvements

## Author
```

---

## 14. README Content Requirements

### 14.1 Overview

Must explain:

```text
RegexFlow AI is a Django + React web app that allows users to upload CSV/Excel files, describe text patterns in natural language, generate regex with an LLM, and apply replacements to selected columns.
```

Also mention optional transformations:

```text
The app also includes LLM-assisted optional transformations:
1. PII Redaction Assistant
2. Phone Number Normalization
```

---

### 14.2 Live Demo Section

Add:

```markdown
## Live Demo

Frontend: https://your-frontend-domain.vercel.app  
Backend Health Check: https://your-backend-domain.com/api/health/
```

---

### 14.3 Demo Video Section

Add one of these:

```markdown
## Demo Video

[Watch the demo video](https://your-video-link)
```

Or, if using an embeddable GitHub-compatible format:

```markdown
https://github.com/user-attachments/assets/your-video-id
```

---

### 14.4 Local Backend Setup

README should include:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

For Windows:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

---

### 14.5 Local Frontend Setup

README should include:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Windows:

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

---

### 14.6 API Documentation

Minimum API table:

| Method | Endpoint                                | Purpose                              |
| ------ | --------------------------------------- | ------------------------------------ |
| GET    | `/api/health/`                          | Backend health check                 |
| POST   | `/api/files/upload/`                    | Upload CSV/XLSX and preview data     |
| POST   | `/api/regex/generate/`                  | Generate regex from natural language |
| POST   | `/api/regex/replace/`                   | Apply regex replacement              |
| POST   | `/api/transformations/pii-redact/`      | Apply PII redaction                  |
| POST   | `/api/transformations/phone-normalize/` | Normalize phone numbers              |

---

### 14.7 LLM Usage Section

Explain:

```text
The LLM is used for:
1. Converting natural language pattern descriptions into Python-compatible regex.
2. Generating structured transformation policies/rules for optional transformations.

The LLM does not directly rewrite uploaded table data. Backend services validate LLM output and execute deterministic transformations.
```

---

### 14.8 Safety and Validation Section

Mention:

```text
- File type validation
- File size limit
- Regex compile validation
- Unsafe regex rejection
- Structured LLM JSON validation
- Deterministic backend execution
- User-friendly frontend errors
- API keys stored only in backend environment variables
```

---

### 14.9 Known Limitations

Suggested limitations:

```markdown
## Known Limitations

- Large-file streaming is not implemented.
- Uploaded files are intended for demo use and may not persist permanently on free hosting platforms.
- Regex generation depends on the configured LLM provider.
- PII detection is practical but not compliance-grade.
- Phone normalization depends on the phonenumbers library and selected default region.
```

---

## 15. Demo Video Plan

### 15.1 Length

Recommended length:

```text
2 to 4 minutes
```

Do not make it too long.

---

### 15.2 Demo Video Script

Use this exact flow:

```text
1. Open deployed frontend.
2. Briefly introduce RegexFlow AI.
3. Upload sample_email_redaction.csv.
4. Show original table preview.
5. Select Email column.
6. Enter natural language: Find email addresses.
7. Generate regex.
8. Show regex and match preview.
9. Enter replacement: REDACTED.
10. Apply replacement.
11. Show processed table and stats.

12. Upload sample_pii_redaction.csv.
13. Open PII Redaction Assistant.
14. Select all PII types.
15. Apply redaction.
16. Show redacted result and stats.

17. Upload sample_phone_normalization.csv.
18. Open Phone Normalization.
19. Enter: Normalize phone numbers to international format.
20. Set default region: AU.
21. Apply normalization.
22. Show normalized result and invalid value handling.

23. Briefly show README and deployed URLs.
```

---

### 15.3 Demo Video Recording Checklist

Before recording:

```text
[ ] Backend deployed and awake
[ ] Frontend deployed
[ ] LLM API key configured
[ ] Sample files ready
[ ] Browser zoom set to 100% or 110%
[ ] No secret values visible
[ ] No local-only URL visible unless explaining local setup
[ ] App starts from clean state
```

---

## 16. Final UI Polish Scope

Only fix issues that affect usability or grading.

Allowed:

```text
button labels
section titles
loading states
error messages
spacing
table readability
empty states
copywriting
```

Not allowed:

```text
new major layout system
new design library
new transformations
new API contracts
new authentication system
```

---

## 17. Final Acceptance Checklist

Phase 6 is complete only when:

### Repository

```text
[ ] GitHub repo is public or accessible to marker
[ ] README.md is complete
[ ] .env.example files exist
[ ] No .env or API keys committed
[ ] Sample datasets exist
[ ] Docs folder contains phase plans
[ ] Unnecessary temporary files removed
```

### Backend

```text
[ ] Backend deploys successfully
[ ] /api/health/ works publicly
[ ] File upload works publicly
[ ] Regex generation works publicly
[ ] Regex replacement works publicly
[ ] PII redaction works publicly
[ ] Phone normalization works publicly
[ ] Backend error responses are structured
[ ] Backend tests pass
```

### Frontend

```text
[ ] Frontend deploys successfully
[ ] Frontend can call deployed backend
[ ] CSV upload works
[ ] XLSX upload works
[ ] Original table preview works
[ ] Processed table display works
[ ] Optional transformations display results
[ ] Friendly errors are displayed
```

### Deliverables

```text
[ ] GitHub source code URL ready
[ ] Public frontend URL ready
[ ] Public backend health-check URL ready
[ ] Demo video embedded or linked in README
[ ] README includes local setup instructions
[ ] README includes deployment notes
[ ] README includes known limitations
```

---

## 18. Risk Register

| Risk                               | Impact                        | Mitigation                                                     |
| ---------------------------------- | ----------------------------- | -------------------------------------------------------------- |
| Backend deploy fails               | No working public URL         | Use simple Railway/Render config and test `/api/health/` first |
| CORS blocks frontend               | App unusable in browser       | Add deployed frontend URL to `CORS_ALLOWED_ORIGINS`            |
| LLM key missing in deployment      | Regex generation fails        | Add backend env vars and test deployed regex generation        |
| Frontend API URL wrong             | Network errors                | Set `VITE_API_BASE_URL` correctly and rebuild                  |
| Free hosting sleeps                | Demo may be slow              | Open backend once before recording demo                        |
| File upload storage not persistent | Processed files may disappear | Document limitation; keep demo flow within same session        |
| README incomplete                  | Poor grading impression       | Follow README checklist exactly                                |
| Secrets exposed                    | Serious issue                 | Check git history and repository before final submission       |

---

## 19. Final Submission Package

Final submission should include:

```text
1. GitHub repository URL
2. Public frontend application URL
3. Public backend health-check URL
4. README with setup instructions
5. README with demo video link
6. README with known limitations
```

---

## 20. Phase Exit Decision

Phase 6 is complete only if:

```text
A marker can open the deployed frontend, upload a sample CSV/XLSX file, generate a regex from natural language, apply replacement, run the two optional transformations, view processed data, and understand setup/deployment from the README.
```

If this is not true, the project is not ready for submission.

````



## 执行判断

Phase 6 只需要一个原则：

```text
Freeze features. Deliver the product.
```

现在最容易翻车的不是功能不足，而是：

```text
CORS 配错
VITE_API_BASE_URL 配错
后端环境变量漏配
README 不完整
demo video 没覆盖 optional transformations
API key 泄露
```

所以 Codex Lead 的重点应该是 **交付工程**，不是继续写新功能。

[1]: https://vercel.com/docs/frameworks/frontend/vite?utm_source=chatgpt.com "Vite on Vercel"
