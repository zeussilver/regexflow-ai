# CDR product data checks QA — 2026-10-12

This work is stacked on PR 2 head `142fc9a`. It is not merged or deployed.
Rules follow Get Products v5 and Get Product Detail v7 of the Consumer Data
Standards v1.36.0, plus the standards-maintenance clarifications #564, #614
and #641.

## Acceptance evidence

| Requirement | Artifact / reproducible evidence | Status |
| --- | --- | --- |
| CDS field types: DateTimeString, RateString, AmountString, URIString, ISO 8601 durations | `CdsTypeTests` | Passed locally |
| 23 rules, each with failing and safe cases; unhashable JSON values reported instead of crashing | `RuleTests` | Passed locally |
| Get Products and Get Product Detail compared; issues found only in Get Products kept once | `RuleTests` | Passed locally |
| Uploads: Get Products, Get Product Detail and array payloads; invalid JSON, `NaN`, empty, oversized, wrong type and too many products rejected without a run | `UploadCheckApiTests` | Passed locally |
| Runs and issues persisted; CSV report contains every issue; response capped at 200 issues | `UploadCheckApiTests` | Passed locally |
| Live checks: allowlisted holders only, `x-v`/`x-min-v` sent, pagination limited to the same host and 20 pages, a 45-second budget for detail requests, failed detail requests reported | `LiveCheckTests` against a local fake data holder | Passed locally |
| The holder's `Date` header is the reference clock for future `lastUpdated` values | `LiveCheckTests` | Passed locally |
| Controlled 406, 5xx, invalid JSON, oversized and unreachable holder errors | `LiveCheckTests` | Passed locally |
| Live checks throttled per client; uploads not throttled | `LiveCheckTests` | Passed locally |
| Content change without a new `lastUpdated` flagged on the next run of the same holder and versions | `LiveCheckTests` | Passed locally |
| Browser: upload the sample, stats, severity filter, exact CSV download, live fixture holder, API error display | `frontend/e2e/product-checks.spec.ts` | Passed locally |
| Original regressions preserved | 87 Django tests and 10 Playwright cases | Passed locally |
| Final remote checks | PR #3 head `f8dca9c` on GitHub Actions | Passed on Actions |

Current totals: 119 Django tests and 13 Playwright cases, run with Python
3.12.12 and Node 22. The commands are in README's Automated regression checks.
The browser run uses the fixed service on 8766 as a synthetic data holder, so no
real bank API is called in CI.

CI passed at https://github.com/zeussilver/regexflow-ai/actions/runs/38148229007
(head `f8dca9c7258b1a95ac52686a1a554d41a80b2390`, Python 3.11.17, Node 22.23.3):
119 Django tests, migration drift check, TypeScript/build and 13 Chromium cases.
Artifact `browser-regression-evidence` holds the synthetic downloads and report;
it expires 2026-10-25.

## Live observation

`python manage.py check_cdr_products` ran against the six configured data holders
on 2026-10-11 between 14:10 and 14:11 UTC. Every holder served Get Products v5 and
Get Product Detail v7, and every listed product's detail was checked.

| Data holder | Products | Products with errors | Errors | Warnings | Main findings |
| --- | ---: | ---: | ---: | ---: | --- |
| ANZ | 37 | 0 | 0 | 25 | `http` links in additional information |
| CommBank | 76 | 19 | 20 | 14 | 15 `lastUpdated` values up to about 10 hours ahead of the API's `Date` header; 3 fees name a `variable` method without the object; 2 links with trailing spaces |
| ING | 14 | 0 | 0 | 0 | — |
| Macquarie Bank | 21 | 4 | 10 | 22 | Links with trailing spaces; Get Products and detail differ for 21 fields such as `effectiveFrom` and descriptions |
| NAB | 35 | 0 | 0 | 1 | One home loan rate without a comparison rate |
| Westpac | 64 | 0 | 0 | 13 | Leading or trailing spaces in names and descriptions; rates without comparison rates |

The future CommBank timestamps were just after midnight on 12 October with a `Z`
suffix while the API reported 14:10 UTC on 11 October. That pattern is consistent
with Sydney local time labelled as UTC, but the cause was not confirmed.

These are point-in-time observations of public endpoints using standards-based
and heuristic rules. They are not a compliance assessment, and data holders may
have changed the data since.

## Loading state

The production backend can take up to a minute to start after a quiet period.
Until the data holders and rules arrived, the workspace said "0 deterministic
rules" and showed an empty data holder list and a disabled button with no
explanation. It now shows a loading message and a placeholder option instead.

| Requirement | Artifact / reproducible evidence | Status |
| --- | --- | --- |
| While the rules request is held, a loading status is shown, "0 deterministic rules" is never shown and Run checks stays disabled; once released, the rule count appears, the status goes and Run checks is enabled | `frontend/e2e/product-checks.spec.ts` ("a slow server shows a loading state instead of zero rules") | Fails on the previous component; passes with the fix |
| Existing regressions preserved | 14 Playwright cases | Passed locally (Python 3.9.6, Node 22) |
