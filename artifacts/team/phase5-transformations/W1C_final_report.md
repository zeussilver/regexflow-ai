# W1C Backend Tests Final Report

## Summary
- Added focused backend API tests for Phase 5 PII redaction and phone normalization.
- Tests target the planned URL names:
  - `transformation-pii-redact`
  - `transformation-phone-normalize`
- Phone normalization tests mock `apps.transformations.phone_rule_service.generate_phone_normalization_rule` and do not call a real LLM.

## Changed Files
- `backend/apps/transformations/tests.py`
- `artifacts/team/phase5-transformations/W1C_final_report.md`

## Test Coverage Added
- PII redaction:
  - email redaction
  - URL redaction
  - phone redaction
  - credit-card-like redaction with Luhn validation
  - null value handling
  - non-target column preservation
  - stats by PII type
  - `UNSUPPORTED_PII_TYPE`
  - `FILE_NOT_FOUND`
  - `COLUMN_NOT_FOUND`
- Phone normalization:
  - AU mobile normalization to E.164
  - AU landline normalization to E.164
  - already-international AU number normalization
  - invalid number preservation
  - `invalid_cells` stats
  - `UNSUPPORTED_TARGET_FORMAT`
  - `LLM_INVALID_JSON`
  - `INVALID_TRANSFORMATION_RULE`
  - `COLUMN_NOT_FOUND`
  - `EMPTY_NATURAL_LANGUAGE`

## Validation
- PASS: `python -m py_compile backend/apps/transformations/tests.py`
- FAIL, expected until W1A runtime is merged: `python manage.py test apps.transformations`
  - Failure: `TypeError: expected str, bytes or os.PathLike object, not NoneType`
  - Cause: `apps.transformations` is only a namespace directory in this isolated W1C branch; W1A has not added the runtime app package/wiring here.
- FAIL, expected until W1A runtime is merged: `python manage.py test apps.transformations.tests`
  - Found 20 tests.
  - PII tests fail with `NoReverseMatch` for `transformation-pii-redact`.
  - Phone tests fail because `apps.transformations.phone_rule_service` is absent.

## Guardrail Status
- Runtime implementation files were not edited.
- Frontend, docs, config, requirements, and checklist files were not edited.
- No real LLM calls are made by the tests.
- Branch was not merged into `phase5-transformations`.

## Risks / Follow-Up
- The tests define the expected response contract for Phase 5. W1A should align implementation response keys with `processed_preview`, `processed_file_id`, `stats`, and the documented error codes.
- Rerun `python manage.py test apps.transformations` from `backend/` after merging W1A runtime wiring.
