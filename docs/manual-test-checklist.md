# Phase 5.5 Manual Test Checklist

Use this checklist before moving to Phase 6. Run the backend and frontend locally, then test with the files in `samples/`.

## Setup

- [ ] Backend is running at the configured API base URL.
- [ ] Frontend is running and points at the backend.
- [ ] No real API keys or secrets are committed.
- [ ] Browser console has no unexpected errors on initial page load.

## Upload And Preview

- [ ] Upload `samples/sample_email_redaction.csv`.
- [ ] Original table preview renders column headers and rows.
- [ ] Upload an `.xlsx` file and confirm the original preview works.
- [ ] Unsupported or invalid files show a user-friendly error.

## Regex Generation And Replacement

- [ ] Generate a regex for `Email` with: `Find email addresses`.
- [ ] Regex result shows a valid pattern, explanation, and match preview.
- [ ] Apply replacement value `REDACTED`.
- [ ] Processed preview renders with redacted email values.
- [ ] Replacement stats show checked rows, matched rows, total matches, and replaced rows.
- [ ] Download CSV is available when `processed_file_id` is returned.
- [ ] Downloaded CSV contains the processed replacement output.

## PII Redaction

- [ ] Upload `samples/sample_pii_redaction.csv`.
- [ ] Leave target columns empty and apply PII redaction.
- [ ] Request succeeds with the default natural-language instruction.
- [ ] Processed preview redacts common email, phone, credit card, and URL values.
- [ ] PII stats render checked, changed, replacement, and by-type counts.
- [ ] Returned PII policy renders in the stats area.
- [ ] Policy shows PII types, target column policy, replacement strategy, and explanation.
- [ ] Download CSV is available when `processed_file_id` is returned.

## Phone Normalization

- [ ] Upload `samples/sample_phone_normalization.csv`.
- [ ] Select the `Phone` column.
- [ ] Keep default region `AU` and target format `E164`.
- [ ] Apply phone normalization.
- [ ] Processed preview normalizes valid AU numbers.
- [ ] Invalid phone values are preserved and counted as invalid.
- [ ] Phone stats render checked, normalized, invalid, and unchanged counts.
- [ ] Download CSV is available when `processed_file_id` is returned.

## Error Handling

- [ ] Empty regex natural-language input shows a user-friendly validation error.
- [ ] Missing replacement prerequisites show a user-friendly validation error.
- [ ] PII redaction with no PII types selected shows a user-friendly validation error.
- [ ] Phone normalization with no target column selected shows a user-friendly validation error.
- [ ] Backend API errors display messages without stack traces.

## Phase 5.5 Gate

- [ ] CSV upload works.
- [ ] XLSX upload works.
- [ ] Natural-language regex generation works for multiple prompt types.
- [ ] Replacement operation works.
- [ ] Processed tables display separately from original previews.
- [ ] PII redaction is LLM-assisted at policy level.
- [ ] Phone normalization is LLM-assisted at rule level.
- [ ] Frontend download links work for processed CSV outputs.
- [ ] Backend tests pass.
- [ ] Frontend build passes.
