# RegexFlow AI User Operation Manual

This manual explains how to test RegexFlow AI without confusing the regex flow, replacement flow, PII redaction assistant, and phone normalization assistant.

Use the sample files in `samples/` when testing:

- `samples/sample_email_redaction.csv` for upload, regex generation, and replacement.
- `samples/sample_pii_redaction.csv` for PII redaction.
- `samples/sample_phone_normalization.csv` for phone normalization.

## 1. Upload A File

1. Open the RegexFlow AI frontend.
2. Choose a `.csv` or `.xlsx` file.
3. Click the upload button.
4. Confirm the original table preview appears.

Expected result:

- The app shows the original file name, column names, row count, and preview rows.
- The original preview is read-only. No data is changed during upload.

Troubleshooting:

- If upload fails, confirm the file is CSV or XLSX.
- Very large files are intentionally limited. Use the sample files for demo testing.

## 2. Generate A Regex From Natural Language

Use this flow when you want the LLM to create a regex pattern for one selected column.

Recommended sample:

- File: `samples/sample_email_redaction.csv`
- Target column: `Email`
- Natural-language prompt: `Find email addresses`

Steps:

1. Upload `samples/sample_email_redaction.csv`.
2. In the regex generation section, select the `Email` column.
3. Enter `Find email addresses`.
4. Click the generate button.
5. Review the generated regex, explanation, and match preview.

Expected result:

- The backend asks the LLM for a regex.
- The backend validates that regex before returning it.
- The UI shows matched examples from the selected column.

Important distinction:

- The regex step only generates and previews a pattern.
- It does not change the file.
- To change data, continue to the replacement step.

## 3. Apply Regex Replacement

Use this flow after a regex has been generated and validated.

Recommended sample:

- File: `samples/sample_email_redaction.csv`
- Target column: `Email`
- Prompt: `Find email addresses`
- Replacement value: `REDACTED`

Steps:

1. Complete the regex generation flow.
2. Enter a replacement value, for example `REDACTED`.
3. Click the replacement button.
4. Review the processed preview and replacement stats.
5. Download the processed CSV if needed.

Expected result:

```text
john.doe@example.com -> REDACTED
```

Replacement stats explain:

- `Checked rows`: rows inspected in the selected column.
- `Matched rows`: rows where at least one match was found.
- `Total matches`: total regex matches.
- `Replaced rows`: rows changed by the replacement.

Important distinction:

- Regex replacement works on one selected column at a time.
- The replacement value is custom text that you type.
- This is different from PII redaction replacement strategy, which uses predefined redaction styles.

## 4. PII Redaction Assistant

Use this flow when you want to redact supported sensitive values such as emails, phone numbers, credit cards, or URLs.

Recommended sample:

- File: `samples/sample_pii_redaction.csv`

The PII redaction assistant has three key controls:

### Target Columns

`Target columns` means where the app should search.

Examples:

- Select `Phone` if phone numbers are stored only in the `Phone` column.
- Select `Phone` and `Notes` if phone numbers may appear in both columns.
- Leave all target columns unselected to let the backend search all text-like columns.

Use a narrow target column selection when testing a specific scenario. Leaving target columns empty is convenient, but it searches a broader area.

### PII Types

`PII types` means what kind of sensitive value the app should look for.

Supported PII types:

- `Email`
- `Phone`
- `Credit card`
- `URL`

Example:

If you only want to redact phone numbers, select only `Phone` under PII types.

Do not select `Email`, `Credit card`, or `URL` unless you also want those values redacted.

### Replacement Strategy

`Replacement strategy` controls what the redacted value becomes.

`Typed placeholders` keeps the sensitive type visible:

```text
0412 345 678 -> [PHONE_REDACTED]
ada@example.com -> [EMAIL_REDACTED]
https://example.com -> [URL_REDACTED]
```

`Generic redacted` uses the same replacement for every supported type:

```text
0412 345 678 -> REDACTED
ada@example.com -> REDACTED
https://example.com -> REDACTED
```

Recommended default:

- Use `Typed placeholders` when testing or demoing because it makes the result easier to inspect.
- Use `Generic redacted` when the output should hide which type of value was removed.

### How To Redact Everyone's Phone Number

If the uploaded file has a `Phone` column and you want to replace every detected phone number:

1. Upload the file.
2. In `Target columns`, select `Phone`.
3. In `PII types`, select only `Phone`.
4. Set `Replacement strategy` to `Typed placeholders`.
5. Click `Apply Redaction`.

Expected result:

```text
0412 345 678 -> [PHONE_REDACTED]
+61 412 345 678 -> [PHONE_REDACTED]
```

If phone numbers may appear in a notes column too:

```text
Target columns: Phone, Notes
PII types: Phone
Replacement strategy: Typed placeholders
```

Important distinction:

- PII redaction removes sensitive values.
- It does not standardize phone-number formatting.
- If you want phone numbers converted to a standard format, use Phone Normalization instead.

## 5. Phone Normalization

Use this flow when you want to reformat phone numbers instead of redacting them.

Recommended sample:

- File: `samples/sample_phone_normalization.csv`
- Target column: `Phone`
- Default region: `AU`
- Target format: `E164`
- Natural-language instruction: `Normalize phone numbers to international format`

Steps:

1. Upload `samples/sample_phone_normalization.csv`.
2. Switch to the Phone Normalization transformation.
3. Select the `Phone` column.
4. Keep default region as `AU`.
5. Keep target format as `E164`.
6. Click the normalize button.
7. Review the processed preview, rule, warnings, and stats.
8. Download the processed CSV if needed.

Expected result:

```text
0412 345 678 -> +61412345678
03 9123 4567 -> +61391234567
abc123 -> abc123
```

Phone normalization stats explain:

- `Checked`: non-empty values inspected.
- `Normalized`: values successfully reformatted.
- `Invalid`: values that could not be parsed as valid phone numbers.
- `Unchanged`: values left as-is.

Important distinction:

- Phone Normalization keeps phone numbers but changes their format.
- PII Redaction hides phone numbers.

## 6. Choosing The Correct Flow

Use this table to avoid common testing mistakes.

| Goal | Use This Flow | Key Settings |
| --- | --- | --- |
| Replace email addresses with custom text | Regex generation + replacement | Target column `Email`, prompt `Find email addresses`, replacement `REDACTED` |
| Redact all phone numbers in a phone column | PII Redaction | Target columns `Phone`, PII types `Phone`, strategy `Typed placeholders` |
| Redact email, phone, card, and URL values across text columns | PII Redaction | Leave target columns empty or select relevant columns; select all PII types |
| Convert phone numbers to `+614...` format | Phone Normalization | Target column `Phone`, region `AU`, format `E164` |
| Preview a pattern without changing data | Regex generation only | Generate regex, do not apply replacement |

## 7. Common Questions

### What is the difference between Target Column and PII Type?

`Target column` answers: where should the app search?

`PII type` answers: what should the app search for?

Example:

```text
Target columns: Phone
PII types: Phone
```

This means: search only the `Phone` column and redact only phone numbers.

### What happens if I leave Target Columns empty in PII Redaction?

The backend searches all text-like columns. This is useful for broad redaction, but it may inspect more columns than expected.

### Why did my phone numbers become `[PHONE_REDACTED]` instead of `+614...`?

You used PII Redaction. That flow hides sensitive values.

Use Phone Normalization if you want to keep phone numbers and standardize their format.

### Why did only one column change after regex replacement?

Regex replacement intentionally applies to one selected column at a time.

Use PII Redaction for multi-column sensitive-value redaction.

### What role does the LLM play?

The LLM suggests a regex, PII policy, or phone-normalization rule. The backend validates the output and performs deterministic processing. The LLM does not directly rewrite table rows.

