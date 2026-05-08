# Phase 6 Final Delivery Manual Test Checklist

Use this checklist before final Phase 6 delivery. Run the local automated checks first, then verify the same core flows against any deployed backend/frontend URLs. Do not mark deployed checks complete unless the deployed URL is known and the behavior is observed there.

## Local Automated Baseline

- [ ] From `backend/`, run `python manage.py test` and record pass/fail plus the number of tests run.
- [ ] From `backend/`, run `python manage.py check` and record pass/fail.
- [ ] From `backend/`, run `python manage.py check --deploy` and record all warnings or errors.
- [ ] From `frontend/`, run `npm run build` and record pass/fail. If it fails because dependencies are missing, record the exact missing command or binary.
- [ ] From `frontend/`, run `npm run lint` if the script exists. If no lint script exists, record that lint is unavailable instead of marking it passed.
- [ ] Run a secret scan or tracked-file grep appropriate for the delivery environment and record the command, result, and any false positives.

## Local Setup

- [ ] Backend starts locally at the configured API base URL.
- [ ] Frontend starts locally and points at the backend.
- [ ] `GET /api/health/` returns a successful health response locally.
- [ ] Browser console has no unexpected errors on initial page load.
- [ ] No real API keys or secrets are committed; only placeholder example values are present in tracked config examples.

## Local Upload And Preview

- [ ] Upload `samples/sample_email_redaction.csv`.
- [ ] Original table preview renders column headers and rows.
- [ ] Upload an `.xlsx` file and confirm the original preview works.
- [ ] Unsupported or invalid files show a user-friendly error.

## Local Regex Generation And Replacement

- [ ] Generate a regex for `Email` with: `Find email addresses`.
- [ ] Regex result shows a valid pattern, explanation, and match preview.
- [ ] Apply replacement value `REDACTED`.
- [ ] Processed preview renders with redacted email values.
- [ ] Replacement stats show checked rows, matched rows, total matches, and replaced rows.
- [ ] Download CSV is available when `processed_file_id` is returned.
- [ ] Downloaded CSV contains the processed replacement output.

## Local PII Redaction

- [ ] Upload `samples/sample_pii_redaction.csv`.
- [ ] Leave target columns empty and apply PII redaction with email, phone, credit card, and URL selected.
- [ ] Request succeeds with the default natural-language instruction.
- [ ] Processed preview redacts common email, phone, credit card, and URL values.
- [ ] PII stats render checked, changed, replacement, and by-type counts.
- [ ] Returned PII policy renders in the stats area.
- [ ] Policy shows PII types, target column policy, replacement strategy, and explanation.
- [ ] Download CSV is available when `processed_file_id` is returned.

## Local Phone Normalization

- [ ] Upload `samples/sample_phone_normalization.csv`.
- [ ] Select the `Phone` column.
- [ ] Keep default region `AU` and target format `E164`.
- [ ] Apply phone normalization.
- [ ] Processed preview normalizes valid AU numbers.
- [ ] Invalid phone values are preserved and counted as invalid.
- [ ] Phone stats render checked, normalized, invalid, and unchanged counts.
- [ ] Download CSV is available when `processed_file_id` is returned.

## Local Error Handling

- [ ] Empty regex natural-language input shows a user-friendly validation error.
- [ ] Missing replacement prerequisites show a user-friendly validation error.
- [ ] PII redaction with no PII types selected shows a user-friendly validation error.
- [ ] Phone normalization with no target column selected shows a user-friendly validation error.
- [ ] Backend API errors display messages without stack traces.

## Deployed Backend Checks

- [ ] Record the deployed backend base URL.
- [ ] `GET <deployed-backend>/api/health/` returns a successful health response.
- [ ] Deployed backend responses do not expose stack traces or debug pages for normal validation errors.
- [ ] Confirm deployment environment uses production-safe secret and debug settings; do not rely on local placeholder settings.

## Deployed Frontend Checks

- [ ] Record the deployed frontend URL.
- [ ] Frontend loads over HTTPS without mixed-content errors.
- [ ] Deployed frontend upload works for `samples/sample_email_redaction.csv`.
- [ ] Deployed frontend upload works for an `.xlsx` file.
- [ ] Deployed frontend regex generation and replacement works end to end.
- [ ] Deployed frontend PII redaction works end to end.
- [ ] Deployed frontend phone normalization works end to end.
- [ ] Download links work for processed CSV outputs.

## README And Demo Video Delivery

- [ ] README includes setup instructions for backend and frontend.
- [ ] README includes local run commands and required environment variables without exposing real secrets.
- [ ] README includes the verified public frontend URL if deployment is complete.
- [ ] README includes the verified public backend URL or API base URL if deployment is complete.
- [ ] README does not claim public deployment if no verified URL is available.
- [ ] Demo video exists, is accessible, and shows upload, regex generation, replacement, PII redaction, phone normalization, and deployed or local URL evidence.
- [ ] Demo video is not claimed complete unless the video link is available and verified.

## Phase 6 Release Gate

- [ ] Backend tests pass or any failures are documented with impact.
- [ ] Backend `check` passes.
- [ ] Backend `check --deploy` warnings are resolved or explicitly documented for the final environment.
- [ ] Frontend build passes or dependency/script blockers are documented with impact.
- [ ] Frontend lint passes if available, or lint is documented as unavailable.
- [ ] CSV upload works locally and, if deployed, on the deployed frontend.
- [ ] XLSX upload works locally and, if deployed, on the deployed frontend.
- [ ] Natural-language regex generation works for the delivery environment.
- [ ] Replacement operation works and downloadable processed CSV output is correct.
- [ ] PII redaction is LLM-assisted at policy level and deterministic at execution level.
- [ ] Phone normalization is LLM-assisted at rule level and deterministic at execution level.
- [ ] Secret checks are complete with no real secrets found in tracked files.
- [ ] README and demo video claims match verified evidence.
