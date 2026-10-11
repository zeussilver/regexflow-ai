# Browser regression QA — 2026-09-13

Scope: PR 1, browser regression and automated PR checks. Historical QA reports
remain unchanged. This is an author/Codex self-review, not a colleague review.

## Reproduction and evidence

Use the exact commands in README, Automated regression checks. CI uses Python
3.11 and Node 22; local verification currently uses Python 3.11.14 and Node 22.23.0.
The final PR description records its head commit and corresponding Actions URL.
Initial full Actions pass: https://github.com/zeussilver/regexflow-ai/actions/runs/34700091648
Final self-review also added explicit model-call assertions to both invalid-upload cases.

| Requirement | Evidence | Status |
| --- | --- | --- |
| Existing Django behavior | 66 tests, isolated settings | Passed locally |
| Real upload → model → replace → download | `frontend/e2e/regression.spec.ts` | Passed locally |
| Empty/unsupported upload after success | Two browser cases | Passed locally |
| Invalid JSON/regex and HTTP 503, retry | Three browser cases | Passed locally |
| 63 rows, only target changes, original bytes intact, repeat | Parsed CSV comparison + server file bytes | Passed locally |
| TypeScript/build | Runner builds real preview artifact | Passed locally |
| Clean-checkout fixtures and ordered CI | `.github/workflows/checks.yml` | Passed on Actions |

## Self-review boundary

The model service is deterministic and local; requests reach it through the real
Django HTTP client. This does not assess provider availability, model quality,
Safari, authentication, tenant isolation, deployment, or production safety.
Reports attach synthetic downloads; failed runs retain screenshots/traces and
service logs for 14 days. No credentials or request bodies are logged.
Four pre-existing untracked demo/walkthrough files are excluded from commits.
No product-flow fixes were needed; disclosure text is added at the
regex generation entry point and in README.
