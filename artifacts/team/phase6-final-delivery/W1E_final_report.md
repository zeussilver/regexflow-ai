# W1E Regression Checklist And Report Preparation

## Scope

- Updated `docs/manual-test-checklist.md` for Phase 6 local and deployed validation.
- Ran available baseline regression checks from the W1E worktree.
- Added this worker report and a lead-owned Phase 6 summary scaffold.
- Did not edit backend implementation/config, frontend implementation/config, README, or `.env` files.

## Checklist Update

The manual checklist now covers:

- Backend `test`, `check`, and `check --deploy`.
- Frontend `build` and `lint` when available.
- Local and deployed `/api/health/` checks.
- CSV and XLSX upload verification.
- Regex generation and replacement.
- PII redaction.
- Phone normalization.
- Secret checks.
- README, public deployment URL, and demo video evidence checks.

## Baseline Command Results

| Command | Result | Notes |
|---|---:|---|
| `cd backend && python manage.py test` | Pass | Found 48 tests. Ran 48 tests in 0.211s. Output ended with `OK`. |
| `cd backend && python manage.py check` | Pass | `System check identified no issues (0 silenced).` |
| `cd backend && python manage.py check --deploy` | Warning-only exit 0 | Reported 5 Django deployment warnings: `security.W004`, `security.W008`, `security.W009`, `security.W016`, `security.W018`. |
| `cd frontend && npm run build` | Fail, dependency missing | Script started `tsc && vite build`, then failed with `sh: tsc: command not found`. `frontend/node_modules` and `node_modules/.bin/tsc` are missing in this worktree. |
| `cd frontend && npm run lint` | Unavailable | Failed with `npm error Missing script: "lint"`. `npm run` lists only `dev`, `build`, and `preview`. |

Frontend build failure output:

```text
> regexflow-ai-frontend@0.1.0 build
> tsc && vite build

sh: tsc: command not found
```

Frontend lint failure output:

```text
npm error Missing script: "lint"
npm error
npm error Did you mean this?
npm error   npm link # Symlink a package folder
npm error
npm error To see a list of scripts, run:
npm error   npm run
npm error A complete log of this run can be found in: /Users/liuzhenqian/.npm/_logs/2026-05-08T14_32_24_001Z-debug-0.log
```

## Deployment Check Details

`python manage.py check --deploy` exited successfully but emitted these warnings:

- `security.W004`: `SECURE_HSTS_SECONDS` is not set.
- `security.W008`: `SECURE_SSL_REDIRECT` is not `True`.
- `security.W009`: `SECRET_KEY` is weak or uses the Django insecure prefix.
- `security.W016`: `CSRF_COOKIE_SECURE` is not `True`.
- `security.W018`: `DEBUG` is `True`.

Impact: local settings are not production-safe as-is. The deployment owner should verify production environment variables/settings before claiming a public deployment is ready.

## Additional Secret-Oriented Checks

Limited secret-pattern scan command:

```sh
git grep -n -E 'sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{20,}|BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY' -- . ':!frontend/package-lock.json'
```

Result: pass for this limited scan. No matches returned for common OpenAI/AWS/Google/private-key signatures. This is not a full secret audit.

Tracked env-file check:

```sh
git ls-files | rg '(^|/)\.env($|\.)'
```

Result: informational. Tracked env example files exist: `backend/.env.example`, `frontend/.env.example`.

## Manual And Deployed Checks

Not run by W1E:

- Browser-based local frontend smoke tests.
- Deployed backend `/api/health/`.
- Deployed frontend CSV/XLSX upload.
- Deployed regex generation/replacement.
- Deployed PII redaction.
- Deployed phone normalization.
- README final validation.
- Demo video verification.

Reason: no verified deployed backend URL, deployed frontend URL, README final diff, or demo video URL was provided in this worker scope. These are now represented in the checklist and scaffold as Lead-owned/TBD.

## Risks And Follow-Up

- Install frontend dependencies, then rerun `npm run build`.
- Add or intentionally omit a frontend lint script; final delivery should document the decision either way.
- Resolve or explicitly accept Django deploy warnings for the actual production environment.
- Lead should rerun integrated validation after all Phase 6 branches are merged.
