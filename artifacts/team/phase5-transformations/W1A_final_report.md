# W1A Backend Final Report

## Changed Files

- `backend/apps/transformations/__init__.py`
- `backend/apps/transformations/apps.py`
- `backend/apps/transformations/urls.py`
- `backend/apps/transformations/views.py`
- `backend/apps/transformations/serializers.py`
- `backend/apps/transformations/pii_patterns.py`
- `backend/apps/transformations/pii_redactor.py`
- `backend/apps/transformations/phone_rule_service.py`
- `backend/apps/transformations/phone_normalizer.py`
- `backend/apps/transformations/transformation_stats.py`
- `backend/config/settings.py`
- `backend/config/urls.py`
- `backend/requirements.txt`
- `artifacts/team/phase5-transformations/W1A_final_report.md`

## Implementation Summary

- Added the `apps.transformations` Django app and wired `/api/transformations/`.
- Added `POST /api/transformations/pii-redact/`.
  - Supports `email`, `phone`, `credit_card`, and `url`.
  - Supports `replacement_strategy` values `typed_placeholders` and `generic_redacted`.
  - Defaults to typed placeholders.
  - Processes supplied `target_columns`, or all text-like columns when `target_columns` is omitted or empty.
  - Returns `NO_TARGET_COLUMNS` when no text-like columns are available.
  - Uses deterministic regex/Luhn logic only; no LLM call is used for PII redaction.
- Added `POST /api/transformations/phone-normalize/`.
  - Requires non-empty `natural_language`.
  - Uses the LLM only to generate a structured phone-normalization rule from column names and at most 10 samples.
  - Applies the rule deterministically with `phonenumbers`.
  - Preserves invalid values by default.
- Added `phonenumbers==8.13.40` to backend requirements.

## Tests Run

- PASS: `python -m compileall backend/apps/transformations backend/config`
- PASS: `python manage.py check`
- PASS: API smoke test for PII redaction with omitted `target_columns`; verified auto-selected text-like columns, placeholders, response transformation, and stats shape.
- PASS: API smoke test for PII redaction with no text-like columns; verified `NO_TARGET_COLUMNS`.
- PASS: API smoke test for phone normalization with a monkeypatched rule generator; verified prompt-schema rule, deterministic E164 formatting, invalid-preserved warning, and stats shape.
- PASS: API smoke test for blank phone `natural_language`; verified `EMPTY_NATURAL_LANGUAGE`.

## Guardrails

- PII redaction is deterministic and does not call the LLM.
- Phone normalization never sends full table data to the LLM; only target column names and up to 10 sample values are sent.
- LLM prompt states: return only valid JSON, no markdown, do not rewrite table data, do not output transformed rows, only generate phone-normalization rules, prefer E164 for international format unless human-readable requested, and preserve invalid by default.
- LLM output is validated for `transformation_type: "phone_normalization"`.
- Row order and non-target columns are preserved by copying the DataFrame before transformation.
- Processed outputs are saved through the existing `save_processed_dataframe` helper.

## Risks And Follow-Up

- Formal backend test files are owned by W1C, so no persistent test cases were added in this worker branch.
- Phone parsing quality depends on `phonenumbers` and the generated/default region. The default region is `AU`.
- Broad deterministic PII patterns intentionally favor practical coverage but may still miss unusual PII formats or match some ambiguous phone-like strings.
