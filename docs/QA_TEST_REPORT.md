# RegexFlow AI QA Test Report

Date: 2026-05-09

Final verdict: **PASS**

Phase 6 delivery is safe to continue after the small PII redaction whitespace bug fixed during QA. Core CSV/XLSX upload, regex generation, regex replacement, PII redaction, and phone normalization flows are covered by automated synthetic tests and pass.

## Test Artifacts Generated

Generated under `tests/fixtures/generated/`:

| Fixture | CSV rows | XLSX rows | Purpose |
| --- | ---: | ---: | --- |
| `mixed_pii_dataset` | 8 | 8 | Mixed email, phone, card-like, URL, address, notes, invoice, date fields |
| `email_cases` | 10 | 10 | Valid, invalid, uppercase, duplicate, blank, null emails |
| `phone_cases` | 9 | 9 | AU mobile/landline, invalid, blank, null phone values |
| `card_cases` | 8 | 8 | Fake/test Luhn-valid and Luhn-invalid card-like values |
| `address_cases` | 8 | 8 | Synthetic AU-style physical address values and negative controls |
| `edge_cases` | 11 | 11 | Unicode, spaces, duplicates, long text, formula-like text, multi-match cells |
| `medium_mixed_dataset` | 600 | 600 | Medium-size mixed dataset |

All data is synthetic. Card-like values are fake/test values only.

## Backend Tests Added

- Upload matrix tests for every generated CSV and XLSX fixture.
- Null JSON serialization test with generated edge fixture.
- Regex generation prompt matrix with mocked LLM output.
- Regex replacement tests for email, phone, URL, card-like, address-like, and multi-match `Notes` cells.
- PII redaction tests on generated CSV/XLSX mixed fixtures with address as negative-control data.
- PII multi-value-in-one-cell regression test.
- Phone normalization tests on generated CSV/XLSX phone fixtures with mocked LLM rule.
- Centralized structured error response tests for required error codes.

No automated test calls a real LLM.

## Frontend / Manual QA

Created `docs/MANUAL_QA_CHECKLIST.md`.

No frontend test framework was introduced. The frontend project has `build` and `preview` scripts only; no `lint` script exists in `frontend/package.json`.

## Commands Executed

| Command | Result | Notes |
| --- | --- | --- |
| `python scripts/generate_test_fixtures.py` | PASS | Generated 14 files |
| `cd backend && python manage.py test` | FAIL | System Python lacks `dj_database_url`; did not reach test execution |
| `cd backend && .venv/bin/python manage.py test` | FAIL then PASS | First run found RF-QA-001; rerun after small fix passed 60 tests |
| `cd frontend && npm install` | PASS | Dependencies already up to date |
| `cd frontend && npm run build` | PASS | TypeScript and Vite build succeeded |
| `cd frontend && npm run lint` | NOT RUN | No lint script exists |

Final backend result:

```text
Found 60 test(s).
Ran 60 tests in 0.555s
OK
```

Final frontend build result:

```text
tsc && vite build
✓ built
```

## Bugs Found

| ID | Severity | Status | Area | Summary |
| --- | --- | --- | --- | --- |
| RF-QA-001 | Medium | Fixed | PII redaction | Credit-card candidate redaction consumed the trailing space after a card-like value inside mixed text |
| RF-QA-ENV-001 | Low | Open environment note | Test environment | `python manage.py test` uses system Python without backend dependencies; project `.venv` works |

### RF-QA-001

Test name:

`apps.transformations.tests.PiiRedactionApiTests.test_generated_edge_fixture_redacts_multiple_pii_values_in_one_cell`

Input file:

`tests/fixtures/generated/edge_cases.csv`

Endpoint:

`POST /api/transformations/pii-redact/`

Request:

- `target_columns`: `["Notes"]`
- `pii_types`: `["email", "phone", "credit_card", "url"]`

Expected result:

`Card [CARD_REDACTED] and phone [PHONE_REDACTED]`

Actual result before fix:

`Card [CARD_REDACTED]and phone [PHONE_REDACTED]`

Suspected cause:

`CREDIT_CARD_CANDIDATE_PATTERN` allowed an optional separator after the final digit, so the match included the following space.

Production code modified:

`backend/apps/transformations/pii_patterns.py`

Exact change:

```python
# before
r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"

# after
r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)"
```

This tightens matching so separators occur only between digits. It does not weaken validation and Luhn validation remains unchanged.

Re-test result:

`cd backend && .venv/bin/python manage.py test` passed all 60 tests.

### RF-QA-ENV-001

Command:

`cd backend && python manage.py test`

Actual result:

`ModuleNotFoundError: No module named 'dj_database_url'`

Severity:

Low, because this is an environment invocation issue and the project-local `backend/.venv` contains the required dependencies.

Recommended fix:

Document that backend commands should use `backend/.venv/bin/python`, or activate the venv before running Django commands.

## Error Codes Covered

- `NO_FILE_UPLOADED`
- `UNSUPPORTED_FILE_TYPE`
- `EMPTY_FILE`
- `FILE_NOT_FOUND`
- `COLUMN_NOT_FOUND`
- `EMPTY_NATURAL_LANGUAGE`
- `LLM_INVALID_JSON`
- `REGEX_COMPILE_ERROR`
- `REGEX_UNSAFE`
- `MISSING_REPLACEMENT`
- `UNSUPPORTED_PII_TYPE`
- `UNSUPPORTED_TARGET_FORMAT`
- `INVALID_TRANSFORMATION_RULE`

## Phase 6 Safety Assessment

PASS: Safe to proceed to final delivery.

Rationale:

- Synthetic CSV and XLSX fixtures upload successfully.
- Table previews return columns, row counts, preview rows, and null-safe JSON.
- Regex generation is validated with mocked LLM outputs.
- Regex replacement modifies only selected columns and preserves original upload data.
- PII redaction deterministically redacts supported PII types and leaves addresses unchanged as negative controls.
- Phone normalization converts valid AU numbers to E.164 and preserves invalid values.
- Backend tests and frontend build pass after the documented small bug fix.
