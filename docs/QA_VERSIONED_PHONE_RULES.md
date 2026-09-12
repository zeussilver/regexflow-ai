# Versioned phone rules QA — 2026-09-13

PR 2 is stacked on PR 1 head `5dae3b4488161d2e031c150fabbcb11c7ecd2d57`,
whose checks passed at https://github.com/zeussilver/regexflow-ai/actions/runs/34700432168.
Neither PR is merged or deployed. Historical QA reports are preserved.

## Acceptance evidence

| Requirement | Artifact / reproducible evidence | Status |
| --- | --- | --- |
| Immutable parameters, defaults, validation and group versions | `apps.rules` ORM + migration; rule API tests | Passed locally |
| Concurrent version allocation | Transactional group counter, unique constraint, concurrent API test + retry, rollback test | Passed locally on SQLite |
| Preview ≤50 rows, full statistics, no stored output | 63-row backend preview test | Passed locally |
| Digest/version binding, 15-minute expiry | Expired/tampered/different-version/file-change tests | Passed locally |
| Synchronous execution metadata, no raw data | Failure, interruption, history schema and 20-record limit tests | Passed locally |
| Processing and write failure | Backend fault injection; real browser output-path failure | Passed locally |
| Save → refresh → new file → preview → execute → exact CSV | `frontend/e2e/phone-rules.spec.ts` and attached synthetic downloads | Passed locally |
| Old version unchanged, file/version clears preview | Browser version and selection assertions | Passed locally |
| No model during reuse | Rejecting local model service; exact zero-call assertion per rule browser case | Passed locally |
| All original regressions preserved | 66 original Django cases + 7 original browser cases | Passed locally |
| Final remote checks | Final head and Actions link recorded in PR description | Pending Actions |

Local environment: Python 3.11.14, Node 22.23.0, matching Playwright Chromium.
Current total: 87 Django tests and 10 Playwright cases. Each browser run uses
one worker and zero retries. Commands are in README's Automated regression checks.
Browser screenshots and exact downloaded CSVs are attached to its HTML report.

## Migration and demo

Run `cd backend && .venv/bin/python manage.py migrate` in the intended environment
before serving this code. The migration only adds three tables and the unique
version constraint. Automated runs use `config.test_settings`, separate SQLite
and media, and synthetic fixtures. No normal local database or hosted service was
migrated as part of this work.

Follow README's Saved phone normalization rules steps. First normalize a
synthetic phone column, save the validated returned parameters, refresh, upload
a different schema retaining that column, preview and confirm. Create NATIONAL
v2, then select E164 v1 to demonstrate immutable history. The browser test also
blocks the output directory, verifies failed metadata/no download, restores it,
and successfully retries after a new preview.

## Self-review and limits

Author/Codex self-review only; no colleague review claimed. Reviewed parameter
allowlisting, error sanitization, original byte preservation, same-byte snapshot
parsing, concurrent allocation, partial failure and React state invalidation.
Selecting a new file unmounts the old rule panel, so a late preview response cannot
restore a confirmation for the wrong file. Version changes clear local preview
and result, and controls are disabled while the request is running.

No samples, prompts, model explanations, raw rows or full exception strings are
stored in these models. IDs, user-supplied rule/column names and timestamps are
still shared metadata, not user isolation. The signature is not authentication.
Valid tokens are reusable for 15 minutes; no exactly-once execution guarantee is
claimed. A process interruption leaves running entries; no recovery scheduler or
output garbage collection is added. Direct database administrators can modify
data; immutability is enforced by the supported write API and model save guard.
PostgreSQL configuration is retained but this run's concurrency evidence is SQLite.
The fixed model proves integration behavior, not real-provider quality. Public
demos must use synthetic data; no production-security or compliance claim is made.
