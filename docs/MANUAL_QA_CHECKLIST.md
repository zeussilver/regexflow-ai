# Manual QA Checklist

Use only synthetic fixtures from `tests/fixtures/generated/`.

## Upload And Preview

- [ ] Upload `mixed_pii_dataset.csv`.
- [ ] Verify table preview renders columns: `ID`, `Name`, `Email`, `Phone`, `CardNumber`, `Website`, `Address`, `Notes`, `InvoiceId`, `DateText`.
- [ ] Verify row count is `8`.
- [ ] Upload `mixed_pii_dataset.xlsx`.
- [ ] Verify the XLSX preview matches the CSV preview and row count is `8`.
- [ ] Upload `edge_cases.csv`.
- [ ] Verify null/empty cells render without frontend crashes.
- [ ] Upload an unsupported file such as `.txt`.
- [ ] Confirm a friendly unsupported file error is shown.

## Regex Generation

- [ ] Select `Email`; generate regex with prompt `Find email addresses`.
- [ ] Confirm a compiled regex and match preview are shown.
- [ ] Select `Phone`; generate regex with prompt `Find Australian phone numbers`.
- [ ] Confirm AU phone examples are matched.
- [ ] Select `Website`; generate regex with prompt `Find URLs`.
- [ ] Confirm URL examples are matched.
- [ ] Select `InvoiceId`; generate regex with prompt `Find values starting with INV-`.
- [ ] Confirm only `INV-` values are matched.
- [ ] Submit an empty natural-language prompt.
- [ ] Confirm a friendly validation error is shown.

## Regex Replacement

- [ ] Apply email regex replacement on `Email` with replacement `REDACTED`.
- [ ] Confirm only the `Email` column changes.
- [ ] Confirm non-target columns remain unchanged.
- [ ] Apply phone regex replacement on `Phone`.
- [ ] Confirm valid AU phone values are replaced.
- [ ] Apply URL regex replacement on `Website`.
- [ ] Confirm URLs are replaced and invalid URL text remains unchanged.
- [ ] Apply card-like regex replacement on `CardNumber`.
- [ ] Confirm card-like candidates are replaced by the general regex workflow.
- [ ] Apply address-like regex replacement on `Address`.
- [ ] Confirm address-like values are replaced by the general regex workflow.
- [ ] Apply a regex to `Notes` that matches both email and phone.
- [ ] Confirm multiple matches in one cell are replaced.
- [ ] Try an invalid regex such as `[`.
- [ ] Confirm a friendly regex compile error is shown.
- [ ] Try an unsafe regex such as `(.+)+`.
- [ ] Confirm a friendly unsafe regex error is shown.
- [ ] Try replacement without the replacement field.
- [ ] Confirm a friendly missing replacement error is shown.

## PII Redaction Assistant

- [ ] Upload `mixed_pii_dataset.csv`.
- [ ] Run PII Redaction Assistant on `Email`, `Phone`, `CardNumber`, `Website`, and `Address`.
- [ ] Select PII types: `email`, `phone`, `credit_card`, `url`.
- [ ] Confirm emails are replaced with `[EMAIL_REDACTED]`.
- [ ] Confirm phone numbers are replaced with `[PHONE_REDACTED]`.
- [ ] Confirm URLs are replaced with `[URL_REDACTED]`.
- [ ] Confirm Luhn-valid card-like values are replaced with `[CARD_REDACTED]`.
- [ ] Confirm Luhn-invalid `1234 5678 9012 3456` remains unchanged.
- [ ] Confirm addresses remain unchanged because address redaction is not an officially supported PII type.
- [ ] Confirm stats by type are shown.
- [ ] Repeat with `mixed_pii_dataset.xlsx`.

## Phone Normalization

- [ ] Upload `phone_cases.csv`.
- [ ] Run Phone Number Normalization on `Phone`.
- [ ] Confirm `0412 345 678` becomes `+61412345678`.
- [ ] Confirm `+61 412 345 678` becomes `+61412345678`.
- [ ] Confirm `03 9123 4567` becomes `+61391234567`.
- [ ] Confirm invalid `12345` remains unchanged.
- [ ] Confirm invalid `abc123` remains unchanged.
- [ ] Confirm `normalized_cells = 5` and `invalid_cells = 2`.
- [ ] Repeat with `phone_cases.xlsx`.
- [ ] Try unsupported format `LOCAL` through the UI if exposed.
- [ ] Confirm a friendly unsupported target format error is shown.
