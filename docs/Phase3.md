下面是可直接放进仓库的 `docs/Phase_3_LLM_Regex_Generation.md`。本 Phase 只实现 **自然语言 → regex pattern**，并在前端展示生成结果；暂时不做真正的数据替换。作业要求中，LLM 需要把自然语言描述转换成 regex pattern，用户之后再指定 replacement 并应用到文本列。

````markdown
# Phase 3 Plan: LLM Regex Generation

Project: RegexFlow AI  
Scope: Natural-language-to-regex generation  
Status: Planned  
Owner: Codex Lead  
Depends on: Phase 1 + Phase 2 completed

---

## 1. Objective

Implement the LLM-powered regex generation layer.

By the end of Phase 3, the user should be able to:

1. Upload and preview a CSV/XLSX file from Phase 1 + 2.
2. Select a target column.
3. Enter a natural language pattern description.
4. Send the request to the backend.
5. Backend calls an LLM to generate a regex pattern.
6. Backend validates the generated regex.
7. Frontend displays:
   - generated regex
   - explanation
   - warning messages if any
   - preview match count on the selected column

This phase does **not** perform replacement yet.

---

## 2. Assignment Requirements Covered

This phase directly covers:

- Creating an API endpoint to receive natural language input.
- Using an LLM to convert natural language into a regex pattern.
- Preparing the frontend input flow for pattern matching.
- Showing the generated regex before applying it.
- Adding backend validation around generated regex.

---

## 3. Non-Goals

Do not implement these in Phase 3:

1. Actual replacement operation.
2. Downloading processed data.
3. Multi-column replacement.
4. User authentication.
5. Large-file streaming.
6. Complex prompt chains.
7. Agentic multi-step transformation.
8. Full optional transformations.

Phase 3 is only about generating and validating regex safely.

---

## 4. Key Design Principle

LLM output must be treated as untrusted.

The LLM should only suggest a regex. The backend must:

1. Parse the LLM output.
2. Validate JSON structure.
3. Validate regex syntax.
4. Limit regex length.
5. Check basic regex safety.
6. Optionally test the regex against preview values.
7. Return the validated result to the frontend.

The backend, not the LLM, remains the source of truth.

---

## 5. Updated Architecture

```text
React Frontend
    |
    | upload file
    v
Django Upload API
    |
    | columns + preview data
    v
React Preview Table
    |
    | selected column + natural language description
    v
Django Regex Generation API
    |
    | prompt construction
    v
LLM Provider
    |
    | structured JSON regex output
    v
Backend Regex Validator
    |
    | regex + explanation + match preview
    v
React Regex Preview Panel
````

---

## 6. Repository Structure Additions

Expected additions:

```text
backend/
└── apps/
    ├── regex_engine/
    │   ├── __init__.py
    │   ├── apps.py
    │   ├── urls.py
    │   ├── views.py
    │   ├── serializers.py
    │   ├── llm_service.py
    │   ├── regex_validator.py
    │   ├── match_preview.py
    │   └── tests.py
    └── files/
        └── services.py

frontend/
└── src/
    ├── api/
    │   └── regex.ts
    ├── components/
    │   ├── RegexGenerationPanel.tsx
    │   ├── RegexPreviewCard.tsx
    │   └── ColumnSelector.tsx
    └── types/
        └── regex.ts
```

---

## 7. Backend API Design

### 7.1 Generate Regex API

Endpoint:

```http
POST /api/regex/generate/
```

Request:

```json
{
  "file_id": "uuid-string",
  "target_column": "Email",
  "natural_language": "Find email addresses"
}
```

Response:

```json
{
  "regex": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,7}\\b",
  "explanation": "Matches common email addresses.",
  "target_column": "Email",
  "match_preview": {
    "checked_rows": 50,
    "matched_rows": 3,
    "examples": [
      {
        "row_index": 0,
        "value": "john.doe@example.com",
        "matches": ["john.doe@example.com"]
      }
    ]
  },
  "warnings": []
}
```

---

### 7.2 Error Response Format

Continue using the same structured format from Phase 1 + 2:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message"
  }
}
```

Required error codes:

| Code                     | Trigger                             |
| ------------------------ | ----------------------------------- |
| `FILE_NOT_FOUND`         | `file_id` does not exist            |
| `COLUMN_NOT_FOUND`       | selected column does not exist      |
| `EMPTY_NATURAL_LANGUAGE` | user input is empty                 |
| `LLM_API_ERROR`          | LLM call fails                      |
| `LLM_INVALID_JSON`       | LLM does not return valid JSON      |
| `REGEX_MISSING`          | LLM response does not contain regex |
| `REGEX_TOO_LONG`         | generated regex exceeds max length  |
| `REGEX_COMPILE_ERROR`    | Python cannot compile regex         |
| `REGEX_UNSAFE`           | regex appears too risky             |
| `INTERNAL_ERROR`         | unexpected backend failure          |

---

## 8. Backend Implementation Plan

### 8.1 Add `regex_engine` Django App

Create app:

```bash
cd backend
python manage.py startapp regex_engine apps/regex_engine
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    "apps.regex_engine",
]
```

Add routes:

```python
# config/urls.py
path("api/regex/", include("apps.regex_engine.urls")),
```

```python
# apps/regex_engine/urls.py
urlpatterns = [
    path("generate/", RegexGenerateView.as_view(), name="regex-generate"),
]
```

---

## 9. Backend Module Responsibilities

### 9.1 `serializers.py`

Create `RegexGenerateSerializer`.

Validate:

* `file_id` is required.
* `target_column` is required.
* `natural_language` is required.
* `natural_language` length should be limited.

Suggested limits:

```text
natural_language min length: 3
natural_language max length: 500
```

---

### 9.2 `llm_service.py`

Responsibilities:

1. Build prompt.
2. Call LLM provider.
3. Force structured JSON output where possible.
4. Parse response.
5. Return normalized dictionary.

Required return shape:

```python
{
    "regex": "...",
    "explanation": "...",
    "flags": [],
    "confidence": "medium"
}
```

Do not allow free-form text as the final output.

---

### 9.3 `regex_validator.py`

Responsibilities:

1. Ensure regex is not empty.
2. Ensure regex is a string.
3. Enforce max regex length.
4. Try `re.compile(regex)`.
5. Reject obviously dangerous patterns.
6. Return warnings where needed.

Suggested max regex length:

```text
300 characters
```

Minimum dangerous-pattern checks:

```text
nested quantifiers:
- (a+)+
- (.*)+
- (.+)+
- ([...]+)+

excessive wildcards:
- .*.*.*
- .{0,100000}

catastrophic-style patterns:
- repeated groups with broad wildcards
```

This does not guarantee perfect regex safety, but it is enough for MVP-level risk reduction.

---

### 9.4 `match_preview.py`

Responsibilities:

1. Load uploaded file by `file_id`.
2. Read DataFrame.
3. Confirm selected column exists.
4. Convert selected column values to strings.
5. Run generated regex on first 50 rows.
6. Return matched row count and examples.

Example return shape:

```python
{
    "checked_rows": 50,
    "matched_rows": 3,
    "examples": [
        {
            "row_index": 0,
            "value": "john.doe@example.com",
            "matches": ["john.doe@example.com"]
        }
    ]
}
```

Limit examples to 5 rows.

---

### 9.5 `views.py`

`RegexGenerateView` flow:

```text
1. Validate request body.
2. Resolve uploaded file path from file_id.
3. Load file preview or DataFrame.
4. Confirm target_column exists.
5. Build LLM prompt using:
   - natural_language
   - target_column
   - column sample values
6. Call LLM service.
7. Parse LLM output.
8. Validate regex.
9. Run match preview.
10. Return regex + explanation + match preview.
```

Keep the view thin. Put business logic into services.

---

## 10. File Lookup Requirement

Phase 1 + 2 saved uploaded files under `media/uploads/`.

Phase 3 needs a reliable way to find a file from `file_id`.

If Phase 1 + 2 already has a file registry/model, reuse it.

If not, implement a simple deterministic lookup:

```text
media/uploads/{file_id}_{original_filename}
```

However, the better design is to introduce a lightweight model:

```python
class UploadedFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="uploads/")
    extension = models.CharField(max_length=10)
    uploaded_at = models.DateTimeField(auto_now_add=True)
```

If Phase 1 + 2 did not create this model, add it now only if it does not disrupt existing upload behavior.

---

## 11. LLM Prompt Contract

The LLM should receive a strict instruction.

Example system instruction:

```text
You are a regex generation assistant for a data-processing web application.

Your task is to convert a user's natural language pattern description into a Python-compatible regular expression.

Return only valid JSON. Do not include markdown. Do not include explanations outside JSON.

The JSON schema is:
{
  "regex": "string",
  "explanation": "string",
  "flags": ["IGNORECASE" | "MULTILINE"],
  "confidence": "low" | "medium" | "high"
}

Rules:
- The regex must be compatible with Python's re module.
- Do not include leading and trailing slash delimiters.
- Prefer safe and readable regex.
- Avoid catastrophic backtracking patterns.
- If the request is ambiguous, still provide the best reasonable regex and set confidence to "low".
- Do not perform replacement.
```

Example user prompt:

```text
Target column: Email

Sample values:
1. john.doe@example.com
2. jane_smith@domain.com
3. alice.brown@website.org

User description:
Find email addresses.
```

Expected LLM output:

```json
{
  "regex": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,7}\\b",
  "explanation": "Matches common email addresses.",
  "flags": [],
  "confidence": "high"
}
```

---

## 12. Environment Variables

Add to `backend/.env.example`:

```env
LLM_PROVIDER=openai_compatible
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=your-model-name
LLM_TIMEOUT_SECONDS=20
```

Do not commit real API keys.

Backend should fail gracefully if the API key is missing.

Suggested error:

```json
{
  "error": {
    "code": "LLM_CONFIG_MISSING",
    "message": "LLM API key is not configured."
  }
}
```

---

## 13. Frontend Plan

### 13.1 New Types

Create `src/types/regex.ts`:

```ts
export interface RegexGenerateRequest {
  file_id: string;
  target_column: string;
  natural_language: string;
}

export interface MatchPreviewExample {
  row_index: number;
  value: string;
  matches: string[];
}

export interface MatchPreview {
  checked_rows: number;
  matched_rows: number;
  examples: MatchPreviewExample[];
}

export interface RegexGenerateResponse {
  regex: string;
  explanation: string;
  target_column: string;
  match_preview: MatchPreview;
  warnings: string[];
}
```

---

### 13.2 New API Client

Create `src/api/regex.ts`:

```ts
import axios from "axios";
import type {
  RegexGenerateRequest,
  RegexGenerateResponse,
} from "../types/regex";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export async function generateRegex(
  payload: RegexGenerateRequest
): Promise<RegexGenerateResponse> {
  const response = await axios.post(`${API_BASE_URL}/regex/generate/`, payload);
  return response.data;
}
```

---

### 13.3 New Components

#### `ColumnSelector.tsx`

Responsibilities:

* Render dropdown from uploaded file columns.
* Store selected column in parent state.
* Disable if no file uploaded.

---

#### `RegexGenerationPanel.tsx`

Responsibilities:

* Show natural language input.
* Show selected column dropdown.
* Generate regex button.
* Loading state.
* Error state.

Input example placeholder:

```text
Find email addresses
```

Other useful placeholders:

```text
Find Australian phone numbers
Find URLs
Find dates in DD/MM/YYYY format
Find values that start with INV-
```

---

#### `RegexPreviewCard.tsx`

Responsibilities:

Display:

* Generated regex
* Explanation
* Target column
* Match count
* Example matches
* Warnings

Do not yet show replacement input in this phase unless visually disabled as “coming next”.

---

## 14. Updated Frontend Page Flow

Current Phase 1 + 2 flow:

```text
Upload file -> Display preview table
```

New Phase 3 flow:

```text
Upload file
    ↓
Display preview table
    ↓
Select target column
    ↓
Enter natural language pattern
    ↓
Generate regex
    ↓
Display generated regex and match preview
```

---

## 15. UX Requirements

Minimum UI behavior:

1. User cannot generate regex before uploading a file.
2. User cannot generate regex without selecting a column.
3. User cannot generate regex with empty natural language input.
4. Button shows loading state while backend calls LLM.
5. Backend errors are shown as friendly messages.
6. Generated regex is easy to copy.
7. Match preview shows whether the regex actually matched sample rows.

---

## 16. Testing Plan

### 16.1 Backend Unit Tests

Mock the LLM service. Do not call the real LLM in tests.

Required tests:

#### Valid Regex Generation

```text
Given:
- valid file_id
- valid target_column
- natural_language = "Find email addresses"

Mock LLM returns:
{
  "regex": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,7}\\b",
  "explanation": "Matches common email addresses.",
  "flags": [],
  "confidence": "high"
}

Expect:
- 200 response
- regex exists
- match_preview exists
- matched_rows > 0
```

#### Missing File

```text
Given invalid file_id
Expect 404 or 400 with FILE_NOT_FOUND
```

#### Missing Column

```text
Given valid file_id but invalid target_column
Expect 400 with COLUMN_NOT_FOUND
```

#### Empty Natural Language

```text
Given empty natural_language
Expect 400 with EMPTY_NATURAL_LANGUAGE
```

#### Invalid LLM JSON

```text
Mock LLM returns invalid JSON
Expect 502 or 500-style controlled error with LLM_INVALID_JSON
```

#### Regex Compile Error

```text
Mock LLM returns invalid regex
Expect 400 with REGEX_COMPILE_ERROR
```

#### Unsafe Regex

```text
Mock LLM returns "(.+)+"
Expect 400 with REGEX_UNSAFE
```

---

### 16.2 Frontend Manual Tests

Required manual checks:

* [ ] Upload CSV.
* [ ] Select Email column.
* [ ] Enter `Find email addresses`.
* [ ] Click Generate Regex.
* [ ] Regex appears.
* [ ] Explanation appears.
* [ ] Match count appears.
* [ ] Example matches appear.
* [ ] Empty input shows validation error.
* [ ] Missing selected column blocks request.
* [ ] Backend error is rendered cleanly.

---

## 17. Acceptance Criteria

Phase 3 is complete only when:

### Backend

* [ ] `POST /api/regex/generate/` exists.
* [ ] Endpoint accepts `file_id`, `target_column`, and `natural_language`.
* [ ] Backend calls LLM through a dedicated service module.
* [ ] LLM output is parsed as structured JSON.
* [ ] Regex is validated before returning.
* [ ] Invalid regex does not reach the frontend as successful output.
* [ ] Endpoint returns match preview from selected column.
* [ ] Backend tests mock LLM calls.
* [ ] No real API key is committed.

### Frontend

* [ ] User can select a target column.
* [ ] User can enter natural language pattern description.
* [ ] User can click Generate Regex.
* [ ] UI shows loading state.
* [ ] UI shows generated regex.
* [ ] UI shows explanation.
* [ ] UI shows match preview.
* [ ] UI shows friendly errors.

### Scope Control

* [ ] No replacement operation is implemented.
* [ ] No download processed file is implemented.
* [ ] No unrelated features are added.

---

## 18. Suggested Commit Plan

```text
commit 1: feat: add regex_engine Django app and routing
commit 2: feat: add LLM service interface and prompt contract
commit 3: feat: add regex validation service
commit 4: feat: add regex generation API endpoint
commit 5: test: add mocked backend tests for regex generation
commit 6: feat: add frontend regex API client and types
commit 7: feat: add column selector and regex generation panel
commit 8: feat: display regex preview and sample matches
commit 9: docs: update README and add Phase 3 notes
```

---

## 19. Risk Register

| Risk                             | Impact                 | Mitigation                                            |
| -------------------------------- | ---------------------- | ----------------------------------------------------- |
| LLM returns non-JSON text        | Backend breaks         | Strict parser and controlled error                    |
| LLM returns invalid regex        | Runtime error          | Compile before returning                              |
| Catastrophic regex               | Slow backend           | Basic unsafe-pattern rejection and preview row limits |
| API key missing                  | Feature fails silently | Return clear `LLM_CONFIG_MISSING`                     |
| Regex does not match user intent | Poor UX                | Show match preview before replacement                 |
| Tests become flaky               | CI instability         | Mock LLM calls in tests                               |
| Overengineering LLM layer        | Delay                  | Use one prompt and one API wrapper only               |

---

## 20. Phase Exit Decision

Phase 3 can exit only if:

```text
A user can upload a CSV/XLSX file, select a column, describe a pattern in natural language, generate a validated regex through the backend LLM service, and see match preview results in the frontend.
```

If this is not true, do not proceed to replacement.

````

