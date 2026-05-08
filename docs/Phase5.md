可以。Phase 5 先定义为 **Optional Transformations Phase**，不做 final polish、不做部署、不做 demo video、不做 README 美化。重点只做两个 optional：**PII Redaction Assistant** 和 **Text Normalization**。这正好对应作业中鼓励使用 LLM 做两个额外数据转换的 optional 要求。

核心设计判断：

1. **PII Redaction 不需要 LLM**：用确定性 regex + validator 更稳定。
2. **Phone Normalization 可以用 LLM 生成 transformation rule**，但后端必须用代码执行规则，不能让 LLM 直接改表格。
3. **所有 transformation 都复用 Phase 4 的 processed preview + stats 模式**。

---

# `docs/Phase_5_Optional_Transformations.md`

````markdown
# Phase 5 Plan: Optional Transformations

Project: RegexFlow AI  
Scope: Optional transformation features only  
Status: Planned  
Owner: Codex Lead  
Depends on: Phase 1 + 2 + 3 + 4 completed

---

## 1. Objective

Implement two optional transformation features:

1. PII Redaction Assistant
2. Text Normalization: phone number normalization

By the end of Phase 5, the user should be able to:

1. Upload a CSV/XLSX file.
2. Preview original data.
3. Use PII Redaction Assistant to automatically redact:
   - email addresses
   - phone numbers
   - credit-card-like numbers
   - URLs
4. Use Text Normalization to normalize phone numbers into an international format.
5. View processed preview data.
6. View transformation statistics.
7. Keep original and processed data separate.

This phase does not include final polish, deployment, demo video, or README beautification.

---

## 2. Non-Goals

Do not implement:

1. Final UI polish.
2. Public deployment.
3. Demo video.
4. Authentication.
5. Full transformation workflow builder.
6. Multi-step chained transformations.
7. Spreadsheet editing.
8. Large-file streaming.
9. Agentic data cleaning.
10. Letting the LLM rewrite table data directly.

Optional if already simple:

- Save processed file and return `processed_file_id`.

If this causes refactoring, defer it.

---

## 3. Key Design Principles

### 3.1 LLM Must Not Rewrite Data

The LLM may generate a structured transformation rule.

The backend must execute the rule deterministically.

Correct:

```text
User prompt
  -> LLM generates rule JSON
  -> backend validates rule
  -> backend applies code-based transformation
````

Wrong:

```text
User prompt + raw table
  -> LLM rewrites table
```

---

### 3.2 PII Redaction Should Be Deterministic

PII redaction should not depend on LLM.

Use backend-defined regex patterns and post-validation rules.

Reasons:

* more predictable
* easier to test
* safer for privacy
* no API cost
* better demo reliability

---

### 3.3 Phone Normalization Should Use Rule Generation + Code Execution

For phone number normalization:

1. User enters natural language such as:

```text
Normalize phone numbers to international format
```

2. LLM returns a rule like:

```json
{
  "transformation_type": "phone_normalization",
  "target_format": "E164",
  "default_region": "AU",
  "preserve_invalid": true,
  "explanation": "Normalize phone numbers to E.164 format using AU as the default region."
}
```

3. Backend validates the rule.
4. Backend uses a phone parsing library or deterministic formatter to normalize values.
5. Invalid phone numbers are left unchanged and counted.

---

## 4. Updated User Flow

```text
Upload CSV/XLSX
    ↓
Preview original data
    ↓
Choose transformation mode
    ↓
Mode A: PII Redaction Assistant
    ↓
Select columns and PII types
    ↓
Apply redaction
    ↓
Display processed preview + stats

OR

Upload CSV/XLSX
    ↓
Preview original data
    ↓
Mode B: Text Normalization
    ↓
Select phone column
    ↓
Enter natural language transformation request
    ↓
LLM generates transformation rule
    ↓
Backend validates rule
    ↓
Backend normalizes phone numbers
    ↓
Display processed preview + stats
```

---

## 5. Backend Architecture

Add a new Django app:

```text
backend/
└── apps/
    └── transformations/
        ├── __init__.py
        ├── apps.py
        ├── urls.py
        ├── views.py
        ├── serializers.py
        ├── pii_patterns.py
        ├── pii_redactor.py
        ├── phone_rule_service.py
        ├── phone_normalizer.py
        ├── transformation_stats.py
        └── tests.py
```

Reuse existing modules from previous phases:

```text
apps/files/services.py
apps/regex_engine/regex_validator.py
apps/regex_engine/llm_service.py
```

---

## 6. New Backend Dependencies

Add:

```text
phonenumbers
```

Update `backend/requirements.txt`:

```text
phonenumbers
```

Purpose:

* Parse local and international phone numbers.
* Normalize to E.164 or international display format.
* Validate phone numbers more reliably than regex-only logic.

---

## 7. Backend API Design

## 7.1 PII Redaction API

Endpoint:

```http
POST /api/transformations/pii-redact/
```

Request:

```json
{
  "file_id": "uuid-string",
  "target_columns": ["Email", "Phone", "Notes"],
  "pii_types": ["email", "phone", "credit_card", "url"],
  "replacement_strategy": "typed_placeholders"
}
```

`target_columns` can be optional.

If omitted, backend should apply redaction to all text-like columns.

Supported `pii_types`:

```text
email
phone
credit_card
url
```

Supported `replacement_strategy`:

```text
typed_placeholders
generic_redacted
```

Recommended default:

```text
typed_placeholders
```

Example replacements:

```text
email       -> [EMAIL_REDACTED]
phone       -> [PHONE_REDACTED]
credit_card -> [CARD_REDACTED]
url         -> [URL_REDACTED]
```

Successful response:

```json
{
  "file_id": "uuid-string",
  "transformation": "pii_redaction",
  "columns": ["ID", "Name", "Email", "Phone", "Notes"],
  "row_count": 3,
  "preview_limit": 50,
  "processed_preview": [
    {
      "ID": 1,
      "Name": "John Doe",
      "Email": "[EMAIL_REDACTED]",
      "Phone": "[PHONE_REDACTED]",
      "Notes": "Website: [URL_REDACTED]"
    }
  ],
  "stats": {
    "checked_cells": 9,
    "changed_cells": 3,
    "total_replacements": 5,
    "by_type": {
      "email": {
        "matches": 1,
        "changed_cells": 1
      },
      "phone": {
        "matches": 1,
        "changed_cells": 1
      },
      "credit_card": {
        "matches": 0,
        "changed_cells": 0
      },
      "url": {
        "matches": 1,
        "changed_cells": 1
      }
    }
  },
  "warnings": []
}
```

---

## 7.2 Phone Normalization API

Endpoint:

```http
POST /api/transformations/phone-normalize/
```

Request:

```json
{
  "file_id": "uuid-string",
  "target_columns": ["Phone"],
  "natural_language": "Normalize phone numbers to international format",
  "default_region": "AU",
  "target_format": "E164"
}
```

`target_format` allowed values:

```text
E164
INTERNATIONAL
NATIONAL
RFC3966
```

Recommended default:

```text
E164
```

Example:

```text
0412 345 678 -> +61412345678
+61 412 345 678 -> +61412345678
03 9123 4567 -> +61391234567
```

Successful response:

```json
{
  "file_id": "uuid-string",
  "transformation": "phone_normalization",
  "rule": {
    "transformation_type": "phone_normalization",
    "target_format": "E164",
    "default_region": "AU",
    "preserve_invalid": true,
    "explanation": "Normalize phone numbers to E.164 format using AU as the default region."
  },
  "columns": ["ID", "Name", "Phone"],
  "row_count": 3,
  "preview_limit": 50,
  "processed_preview": [
    {
      "ID": 1,
      "Name": "John Doe",
      "Phone": "+61412345678"
    }
  ],
  "stats": {
    "checked_cells": 3,
    "normalized_cells": 2,
    "invalid_cells": 1,
    "unchanged_cells": 1
  },
  "warnings": [
    "1 value could not be parsed as a valid phone number and was left unchanged."
  ]
}
```

---

## 8. Error Response Format

Use the same project-wide error format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message"
  }
}
```

Required error codes:

```text
FILE_NOT_FOUND
COLUMN_NOT_FOUND
NO_TARGET_COLUMNS
UNSUPPORTED_PII_TYPE
UNSUPPORTED_REPLACEMENT_STRATEGY
EMPTY_NATURAL_LANGUAGE
LLM_CONFIG_MISSING
LLM_API_ERROR
LLM_INVALID_JSON
INVALID_TRANSFORMATION_RULE
UNSUPPORTED_TARGET_FORMAT
INVALID_DEFAULT_REGION
FILE_PARSE_ERROR
INTERNAL_ERROR
```

---

## 9. PII Redaction Design

### 9.1 Pattern Types

Implement in `pii_patterns.py`.

#### Email

Use a standard email regex:

```text
\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b
```

#### URL

Use a practical URL regex:

```text
https?://[^\s]+|www\.[^\s]+
```

#### Credit-Card-Like Numbers

Detect candidates:

```text
13 to 19 digits, optionally separated by spaces or hyphens
```

Then apply Luhn validation by default to reduce false positives.

Important:

* This is not a payment compliance feature.
* It is only a redaction helper for assignment/demo purposes.

#### Phone Numbers

Use a broad candidate pattern, then filter by digit count.

Candidate logic:

```text
+ optional country code
digits, spaces, brackets, hyphens, dots
minimum 8 digits
maximum 15 digits
```

Recommended:

```text
(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)
```

Post-filter:

```text
digits count between 8 and 15
```

---

### 9.2 Redaction Order

Apply patterns in this order:

```text
1. URL
2. Email
3. Credit card
4. Phone
```

Reason:

* Phone regex is broad and may accidentally match card-like numbers.
* URL and email should be handled before generic numeric patterns.

---

### 9.3 PII Redaction Processor

Implement:

```python
def redact_pii_in_dataframe(
    df,
    target_columns,
    pii_types,
    replacement_strategy="typed_placeholders",
    preview_limit=50,
) -> dict:
    ...
```

Responsibilities:

1. Copy DataFrame.
2. Resolve target columns.
3. Convert selected cell values to strings safely.
4. Apply selected PII detectors.
5. Replace matched values.
6. Count replacements.
7. Return processed preview and stats.
8. Preserve non-target columns.
9. Preserve row order.

---

## 10. Phone Normalization Design

### 10.1 LLM Rule Contract

LLM must return only JSON.

Expected schema:

```json
{
  "transformation_type": "phone_normalization",
  "target_format": "E164",
  "default_region": "AU",
  "preserve_invalid": true,
  "explanation": "string"
}
```

Allowed `transformation_type`:

```text
phone_normalization
```

Allowed `target_format`:

```text
E164
INTERNATIONAL
NATIONAL
RFC3966
```

Allowed `default_region`:

```text
Two-letter country or region code, e.g. AU, US, GB, CN
```

If the LLM returns anything else, reject it.

---

### 10.2 LLM Prompt

System instruction:

```text
You are a transformation rule generator for a data-processing web application.

Your task is to convert a user's natural language request into a structured phone-normalization rule.

Return only valid JSON.
Do not include markdown.
Do not rewrite table data.
Do not output transformed rows.

The JSON schema is:
{
  "transformation_type": "phone_normalization",
  "target_format": "E164" | "INTERNATIONAL" | "NATIONAL" | "RFC3966",
  "default_region": "two-letter region code",
  "preserve_invalid": true,
  "explanation": "string"
}

Rules:
- Only generate rules for phone number normalization.
- If the user asks for international format, prefer E164 unless the user explicitly asks for human-readable formatting.
- Use the provided default region if the input numbers appear local.
- Invalid phone numbers should be preserved by default.
```

User prompt example:

```text
Target columns: Phone

Default region: AU

Sample values:
1. 0412 345 678
2. +61 412 345 678
3. 03 9123 4567

User request:
Normalize phone numbers to international format
```

Expected LLM output:

```json
{
  "transformation_type": "phone_normalization",
  "target_format": "E164",
  "default_region": "AU",
  "preserve_invalid": true,
  "explanation": "Normalize Australian local and international phone numbers to E.164 format."
}
```

---

### 10.3 Phone Normalizer

Implement:

```python
def normalize_phone_numbers_in_dataframe(
    df,
    target_columns,
    rule,
    preview_limit=50,
) -> dict:
    ...
```

Execution rules:

1. Copy DataFrame.
2. Process only target columns.
3. Convert values to string.
4. Skip empty values.
5. Use `phonenumbers.parse(value, default_region)`.
6. Check `phonenumbers.is_valid_number(parsed)`.
7. Format using requested `target_format`.
8. If invalid and `preserve_invalid=true`, leave unchanged.
9. Return processed preview and stats.

---

## 11. Frontend Plan

Add transformation UI after existing regex replacement workflow.

Expected structure:

```text
frontend/
└── src/
    ├── api/
    │   └── transformations.ts
    ├── types/
    │   └── transformations.ts
    ├── components/
    │   ├── TransformationModeTabs.tsx
    │   ├── PiiRedactionPanel.tsx
    │   ├── PhoneNormalizationPanel.tsx
    │   ├── TransformationStatsCard.tsx
    │   └── TransformationResultTable.tsx
    └── pages/
        └── HomePage.tsx
```

---

## 12. Frontend UI Requirements

### 12.1 Transformation Mode Tabs

Modes:

```text
Regex Replacement
PII Redaction Assistant
Phone Normalization
```

If the current UI is already large, keep it simple:

```text
Optional Transformations
  - PII Redaction Assistant
  - Phone Normalization
```

---

### 12.2 PII Redaction Panel

Fields:

```text
Target columns: multi-select
PII types: checkboxes
Replacement strategy: dropdown
Apply Redaction button
```

Default selected PII types:

```text
email
phone
credit_card
url
```

Default replacement strategy:

```text
typed_placeholders
```

---

### 12.3 Phone Normalization Panel

Fields:

```text
Target columns: multi-select or single-select
Natural language instruction input
Default region input/dropdown
Target format dropdown
Normalize button
```

Default values:

```text
natural_language = "Normalize phone numbers to international format"
default_region = "AU"
target_format = "E164"
```

---

## 13. Frontend State Rules

When user uploads a new file:

```text
clear regex result
clear replacement result
clear PII redaction result
clear phone normalization result
```

When user applies a new transformation:

```text
do not mutate original preview
show processed result in a separate table
```

When transformation fails:

```text
keep original preview visible
show friendly error
do not show raw stack traces
```

---

## 14. Backend Tests

### 14.1 PII Redaction Tests

Required tests:

1. Redacts email addresses.
2. Redacts URLs.
3. Redacts phone numbers.
4. Redacts credit-card-like numbers.
5. Does not crash on null values.
6. Preserves non-target columns.
7. Returns correct stats.
8. Unsupported PII type returns `UNSUPPORTED_PII_TYPE`.
9. Missing file returns `FILE_NOT_FOUND`.
10. Missing column returns `COLUMN_NOT_FOUND`.

Example test data:

```csv
ID,Name,Email,Phone,Card,Website
1,John Doe,john.doe@example.com,0412 345 678,4111 1111 1111 1111,https://example.com
2,Jane Smith,jane@example.org,+61 412 345 678,not-a-card,www.website.org
```

Expected:

```text
Email -> [EMAIL_REDACTED]
Phone -> [PHONE_REDACTED]
Card -> [CARD_REDACTED] if Luhn-valid
Website -> [URL_REDACTED]
```

---

### 14.2 Phone Normalization Tests

Mock the LLM service.

Required tests:

1. Valid LLM rule normalizes AU mobile number.
2. Valid LLM rule normalizes AU landline number.
3. Already international number is normalized consistently.
4. Invalid number is preserved.
5. Invalid number increments `invalid_cells`.
6. Unsupported target format returns `UNSUPPORTED_TARGET_FORMAT`.
7. Invalid LLM JSON returns `LLM_INVALID_JSON`.
8. Wrong transformation type returns `INVALID_TRANSFORMATION_RULE`.
9. Missing target column returns `COLUMN_NOT_FOUND`.
10. Empty natural language returns `EMPTY_NATURAL_LANGUAGE`.

Example input:

```csv
ID,Name,Phone
1,John Doe,0412 345 678
2,Jane Smith,+61 412 345 678
3,Alice Brown,03 9123 4567
4,Bad Value,abc123
```

Expected E164 output:

```text
+61412345678
+61412345678
+61391234567
abc123
```

---

## 15. Manual Frontend Testing

### PII Redaction

* [ ] Upload CSV with email, phone, URL, and card-like values.
* [ ] Select PII Redaction Assistant.
* [ ] Select all PII types.
* [ ] Apply redaction.
* [ ] Processed table shows placeholders.
* [ ] Stats show correct replacement counts.
* [ ] Original table remains visible.

### Phone Normalization

* [ ] Upload CSV with phone numbers.
* [ ] Select Phone column.
* [ ] Enter `Normalize phone numbers to international format`.
* [ ] Set default region to `AU`.
* [ ] Apply normalization.
* [ ] Processed table shows normalized phone numbers.
* [ ] Invalid values remain unchanged.
* [ ] Stats show normalized and invalid counts.
* [ ] Original table remains visible.

---

## 16. Acceptance Criteria

Phase 5 is complete only when:

### PII Redaction

* [ ] `/api/transformations/pii-redact/` exists.
* [ ] Backend redacts email addresses.
* [ ] Backend redacts phone numbers.
* [ ] Backend redacts credit-card-like numbers.
* [ ] Backend redacts URLs.
* [ ] Backend returns processed preview.
* [ ] Backend returns stats by PII type.
* [ ] Frontend provides PII redaction UI.
* [ ] Frontend displays processed result and stats.

### Phone Normalization

* [ ] `/api/transformations/phone-normalize/` exists.
* [ ] Backend calls LLM only to generate a rule.
* [ ] Backend validates the LLM-generated rule.
* [ ] Backend executes normalization deterministically.
* [ ] Backend does not let LLM rewrite table rows.
* [ ] Backend normalizes valid phone numbers.
* [ ] Backend preserves invalid values.
* [ ] Backend returns processed preview and stats.
* [ ] Frontend provides phone normalization UI.
* [ ] Frontend displays processed result and stats.

### Scope Control

* [ ] No final polish.
* [ ] No deployment.
* [ ] No demo video.
* [ ] No authentication.
* [ ] No unrelated UI redesign.
* [ ] No secrets committed.

---

## 17. Suggested Commit Plan

```text
commit 1: feat: add transformations app and routes
commit 2: feat: add PII detection patterns and redaction service
commit 3: feat: add PII redaction API endpoint
commit 4: test: add PII redaction backend tests
commit 5: feat: add phone normalization rule service
commit 6: feat: add deterministic phone normalization processor
commit 7: feat: add phone normalization API endpoint
commit 8: test: add phone normalization backend tests with mocked LLM
commit 9: feat: add frontend transformation API and types
commit 10: feat: add PII redaction frontend panel
commit 11: feat: add phone normalization frontend panel
commit 12: chore: update minimal docs and env examples
```

---

## 18. Phase Exit Decision

Phase 5 can exit only if:

```text
A user can upload a CSV/XLSX file, apply PII redaction, apply phone normalization through an LLM-generated rule, and see processed previews plus transformation statistics in the frontend.
```

If this is not true, do not move to final polish, deployment, README completion, or demo video.

````



## 关键执行策略

Phase 5 不应该变成“大而全的数据清洗平台”。这一步只做两个有展示价值、能写进 README 的 optional：

| Feature                 |    是否用 LLM | 后端执行方式                                        |
| ----------------------- | ---------: | --------------------------------------------- |
| PII Redaction Assistant |          否 | regex + validator + deterministic replacement |
| Phone Normalization     | 是，仅生成 rule | `phonenumbers` + deterministic formatting     |

Phase 5 跑通后，再进入 **Phase 6：download processed file + README + deployment + demo video + final polish**。
