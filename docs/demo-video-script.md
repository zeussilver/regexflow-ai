# Demo Video Script

Target length: 2-4 minutes.

## Pre-Recording Checklist

- Public backend is deployed and awake.
- Public frontend is deployed and points to the backend with `VITE_API_BASE_URL=https://<backend-host>/api`.
- Backend LLM variables are configured in the backend deployment environment with non-placeholder values.
- For a local fallback recording only, backend is running at `http://localhost:8000`, frontend is running at `http://localhost:5173`, and `frontend/.env` points to `VITE_API_BASE_URL=http://localhost:8000/api`.
- Browser console has no unexpected startup errors.
- The `samples/` folder is visible and ready:
  - `samples/sample_email_redaction.csv`
  - `samples/sample_pii_redaction.csv`
  - `samples/sample_phone_normalization.csv`
- README placeholders for deployed frontend, backend, and demo video are not presented as live links unless the integration lead has verified real URLs.
- No secrets, terminal API keys, or private environment files are visible on screen.

## Recording Flow

### 0:00-0:20 - Open README And App

Show the README title and the Live Demo / Demo Video sections.

Voiceover:

"This is RegexFlow AI, a Django and React app for AI-assisted regex and data transformation workflows. The README links to the deployed frontend, deployed backend API, and this demo video once the final integration lead has verified those links."

Open the deployed frontend URL. If public deployment is not available yet, use `http://localhost:5173` and state that this is a local fallback recording.

### 0:20-1:10 - Upload And Regex Generation

Upload `samples/sample_email_redaction.csv`.

Voiceover:

"First, I upload a CSV file. The backend parses it with pandas and returns the detected columns plus a preview of the first rows."

Select the `Email` column. Enter:

```text
Find email addresses
```

Click the regex generation button.

Voiceover:

"Now I ask the LLM for a regex, but the LLM only proposes a structured JSON result. The backend validates the returned Python-compatible regex, compiles it, checks supported flags, rejects unsafe patterns, and builds a match preview before any replacement is applied."

Point out the regex, explanation, match counts, and example matches.

### 1:10-1:45 - Regex Replacement

Use replacement value:

```text
REDACTED
```

Apply the replacement.

Voiceover:

"The replacement step is deterministic backend code. The LLM does not rewrite the table. The backend applies the validated regex to the selected column, returns a processed preview, and reports checked rows, matched rows, total matches, and replaced rows."

Show the processed preview and stats.

### 1:45-2:30 - PII Redaction Assistant

Upload `samples/sample_pii_redaction.csv`.

Select the PII redaction mode. Leave the default PII types enabled: email, phone, credit card, and URL. Use typed placeholders.

Apply PII redaction.

Voiceover:

"The PII Redaction Assistant uses the LLM at the policy level only. It selects supported policy options, then backend detectors redact emails, phone numbers, valid credit-card candidates, and URLs. This is practical demo redaction, not a compliance-grade PII system."

Show typed placeholders, the policy summary, by-type stats, and any warnings.

### 2:30-3:15 - Phone Normalization

Upload `samples/sample_phone_normalization.csv`.

Switch to phone normalization. Select the `Phone` column. Keep:

```text
Default region: AU
Target format: E164
Instruction: Normalize phone numbers to international format
```

Apply normalization.

Voiceover:

"Phone normalization uses a bounded LLM-generated rule and then the backend runs the `phonenumbers` library. Valid Australian numbers are normalized to E164, and invalid values are preserved by default with stats and warnings."

Show normalized valid values, the preserved invalid value, and stats.

### 3:15-3:40 - Close On Documentation

Return briefly to the README API Documentation and Known Limitations sections.

Voiceover:

"The README documents the six grading endpoints, local setup, environment variables, LLM usage, validation behavior, sample datasets, testing, deployment placeholders, and known limitations. The main limitations are that large-file streaming is not implemented, uploads are intended for demo use, file persistence depends on hosting, and LLM-backed features require a configured provider."

End recording.

## Post-Recording Checks

- Video shows upload, regex generation, replacement, PII redaction, and phone normalization.
- README Live Demo and Demo Video sections are visible.
- No fake public URL is claimed as live.
- No secrets or private keys are visible.
- Audio mentions that the LLM does not directly rewrite table data.
- Final video length is between 2 and 4 minutes.
