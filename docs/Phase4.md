下面进入 **Phase 4：Regex Replacement Operation**。

这一阶段的目标是把 Phase 3 已经生成并验证过的 regex 真正用于数据处理：用户输入 replacement value，后端对目标列执行替换，返回处理后的表格、匹配数量，并在前端展示结果。这个阶段直接对应作业要求里的 “users specify the replacement value” 和 “application replaces the matched patterns in the text columns and displays the updated data”。

---

# `docs/Phase_4_Regex_Replacement.md`

````markdown
# Phase 4 Plan: Regex Replacement Operation

Project: RegexFlow AI  
Scope: Apply validated regex to selected column and display processed data  
Status: Planned  
Owner: Codex Lead  
Depends on: Phase 1 + 2 + 3 completed

---

## 1. Objective

Implement the actual pattern replacement workflow.

By the end of Phase 4, the user should be able to:

1. Upload a CSV/XLSX file.
2. Preview the uploaded data.
3. Select a target column.
4. Generate a regex from natural language through the LLM.
5. Enter a replacement value.
6. Apply the regex replacement to the selected column.
7. View the processed table.
8. See replacement statistics:
   - checked rows
   - matched rows
   - total matches
   - replaced rows
9. Keep the original preview and processed preview visually separate.

This phase focuses on the replacement operation only.

---

## 2. Assignment Requirements Covered

This phase directly covers:

- User specifies the replacement value.
- Application replaces matched patterns in text columns.
- Updated data is displayed in tabular format.
- Backend handles data processing logic.
- Frontend shows processed data after replacement.

---

## 3. Non-Goals

Do not implement the following in this phase unless explicitly marked as optional:

1. User authentication.
2. Deployment.
3. Demo video.
4. Multi-file batch processing.
5. Large-file streaming.
6. Advanced transformation workflows.
7. Full audit history.
8. Complex database versioning.

Optional if easy:
- Download processed CSV.

If download adds too much complexity, defer it to Phase 5.

---

## 4. Current System State

Phase 1 + 2 already provides:

- Django backend.
- React frontend.
- File upload.
- CSV/XLSX parsing.
- Table preview.
- `file_id`.

Phase 3 already provides:

- Target column selection.
- Natural-language input.
- LLM-generated regex.
- Regex validation.
- Match preview.

Phase 4 adds:

- Replacement value input.
- Backend replacement API.
- Processed table response.
- Frontend processed-data display.

---

## 5. Updated User Flow

```text
Upload CSV/XLSX
    ↓
Preview original table
    ↓
Select target column
    ↓
Describe pattern in natural language
    ↓
Generate regex
    ↓
Preview regex matches
    ↓
Enter replacement value
    ↓
Apply replacement
    ↓
Display processed table
    ↓
Show replacement statistics
````

---

## 6. Backend API Design

### 6.1 Apply Replacement API

Endpoint:

```http
POST /api/regex/replace/
```

Request:

```json
{
  "file_id": "uuid-string",
  "target_column": "Email",
  "regex": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,7}\\b",
  "replacement": "REDACTED"
}
```

Successful response:

```json
{
  "file_id": "uuid-string",
  "target_column": "Email",
  "regex": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,7}\\b",
  "replacement": "REDACTED",
  "columns": ["ID", "Name", "Email"],
  "row_count": 3,
  "preview_limit": 50,
  "processed_preview": [
    {
      "ID": 1,
      "Name": "John Doe",
      "Email": "REDACTED"
    },
    {
      "ID": 2,
      "Name": "Jane Smith",
      "Email": "REDACTED"
    },
    {
      "ID": 3,
      "Name": "Alice Brown",
      "Email": "REDACTED"
    }
  ],
  "stats": {
    "checked_rows": 3,
    "matched_rows": 3,
    "total_matches": 3,
    "replaced_rows": 3
  },
  "warnings": []
}
```

---

## 7. Backend Error Response Format

Use the same error format as earlier phases:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message"
  }
}
```

Required error codes:

| Code                  | Trigger                                                         |
| --------------------- | --------------------------------------------------------------- |
| `FILE_NOT_FOUND`      | `file_id` does not map to an uploaded file                      |
| `COLUMN_NOT_FOUND`    | selected column does not exist                                  |
| `EMPTY_REGEX`         | regex is empty                                                  |
| `EMPTY_REPLACEMENT`   | replacement is missing if policy requires non-empty replacement |
| `REGEX_TOO_LONG`      | regex exceeds max length                                        |
| `REGEX_COMPILE_ERROR` | Python cannot compile regex                                     |
| `REGEX_UNSAFE`        | regex rejected by validator                                     |
| `NO_MATCHES_FOUND`    | regex compiles but matches no rows                              |
| `FILE_PARSE_ERROR`    | uploaded file cannot be read                                    |
| `INTERNAL_ERROR`      | unexpected backend failure                                      |

Important design decision:

* Empty replacement can be valid if the user wants to delete matched text.
* Therefore, `replacement` may be an empty string.
* Only reject replacement if the field is completely missing.

---

## 8. Backend Modules

Expected additions or modifications:

```text
backend/
└── apps/
    └── regex_engine/
        ├── urls.py
        ├── views.py
        ├── serializers.py
        ├── regex_validator.py
        ├── replacement_processor.py
        └── tests.py
```

---

## 9. Backend Implementation Details

### 9.1 `serializers.py`

Add `RegexReplaceSerializer`.

Required fields:

```python
file_id: str
target_column: str
regex: str
replacement: str
```

Validation rules:

* `file_id` required.
* `target_column` required.
* `regex` required.
* `replacement` field must exist.
* `replacement` can be empty string.
* `regex` max length should reuse Phase 3 setting, recommended 300 chars.

---

### 9.2 `replacement_processor.py`

Create a dedicated replacement service.

Required function:

```python
def apply_regex_replacement(
    df: pd.DataFrame,
    target_column: str,
    regex: str,
    replacement: str,
    preview_limit: int = 50,
) -> dict:
    ...
```

Responsibilities:

1. Confirm target column exists.
2. Convert target column values to strings safely.
3. Apply compiled regex with `re.subn`.
4. Count:

   * checked rows
   * matched rows
   * total matches
   * replaced rows
5. Return processed DataFrame preview.
6. Preserve non-target columns.
7. Preserve row order.
8. Avoid mutating the original DataFrame in-place unless explicitly intended.

---

### 9.3 Replacement Counting Rules

Use `re.subn()` per cell.

Example logic:

```python
new_value, count = compiled_regex.subn(replacement, original_value)
```

Definitions:

| Metric          | Meaning                                               |
| --------------- | ----------------------------------------------------- |
| `checked_rows`  | Number of rows checked in the selected column         |
| `matched_rows`  | Number of rows where regex matched at least once      |
| `total_matches` | Total number of regex matches across all checked rows |
| `replaced_rows` | Number of rows whose value changed                    |

Usually:

```text
matched_rows == replaced_rows
```

But keep them separate because a zero-width regex or unusual replacement could produce edge cases.

---

### 9.4 Null and Non-String Handling

Rules:

1. If cell value is `NaN`, `None`, or `NaT`, treat it as empty string for processing.
2. Convert non-null values to `str`.
3. Only process the target column.
4. Leave other columns unchanged as much as possible.

Recommended behavior:

```text
None / NaN -> ""
12345 -> "12345"
john@example.com -> "john@example.com"
```

This is acceptable because regex replacement is text-oriented.

---

### 9.5 Regex Validation

Reuse Phase 3 `regex_validator.py`.

Before replacement:

1. Validate regex is not empty.
2. Validate regex length.
3. Compile regex.
4. Reject unsafe patterns.
5. Return structured error if invalid.

Do not duplicate validator logic inside the view.

---

### 9.6 `views.py`

Add:

```python
class RegexReplaceView(APIView):
    def post(self, request):
        ...
```

Flow:

```text
1. Validate request body.
2. Locate uploaded file using file_id.
3. Read file into DataFrame.
4. Validate selected column exists.
5. Validate regex.
6. Apply replacement.
7. Normalize processed preview for JSON.
8. Return processed preview + stats.
```

Keep the view thin.

---

### 9.7 URL Routing

Update `apps/regex_engine/urls.py`:

```python
urlpatterns = [
    path("generate/", RegexGenerateView.as_view(), name="regex-generate"),
    path("replace/", RegexReplaceView.as_view(), name="regex-replace"),
]
```

---

## 10. Processed Data Persistence

Phase 4 has two possible designs.

### Option A: Stateless Response Only

The backend applies replacement and returns processed preview only.

Pros:

* Simple.
* Fast to implement.
* Enough for visual demo.

Cons:

* Cannot download full processed file later unless replacement is re-run.
* Processed state only exists in frontend memory.

### Option B: Save Processed File

The backend applies replacement, saves a processed CSV under `media/processed/`, and returns `processed_file_id`.

Pros:

* Prepares for download.
* Better for Phase 5.
* More complete product flow.

Cons:

* Slightly more implementation work.

Recommended:

Use **Option B** if the current file storage design is already stable.

Suggested response extension:

```json
{
  "processed_file_id": "uuid-string"
}
```

Suggested file path:

```text
media/processed/{processed_file_id}.csv
```

If this causes too much refactoring, use Option A and defer saving to Phase 5.

---

## 11. Frontend Plan

Expected additions or modifications:

```text
frontend/
└── src/
    ├── api/
    │   └── regex.ts
    ├── types/
    │   └── regex.ts
    ├── components/
    │   ├── ReplacementPanel.tsx
    │   ├── ProcessedDataTable.tsx
    │   └── ReplacementStatsCard.tsx
    └── pages/
        └── HomePage.tsx
```

---

## 12. Frontend Type Definitions

Add to `src/types/regex.ts`:

```ts
export interface RegexReplaceRequest {
  file_id: string;
  target_column: string;
  regex: string;
  replacement: string;
}

export interface ReplacementStats {
  checked_rows: number;
  matched_rows: number;
  total_matches: number;
  replaced_rows: number;
}

export interface RegexReplaceResponse {
  file_id: string;
  processed_file_id?: string;
  target_column: string;
  regex: string;
  replacement: string;
  columns: string[];
  row_count: number;
  preview_limit: number;
  processed_preview: Record<string, string | number | boolean | null>[];
  stats: ReplacementStats;
  warnings: string[];
}
```

---

## 13. Frontend API Client

Update `src/api/regex.ts`:

```ts
export async function applyReplacement(
  payload: RegexReplaceRequest
): Promise<RegexReplaceResponse> {
  const response = await axios.post(`${API_BASE_URL}/regex/replace/`, payload);
  return response.data;
}
```

---

## 14. Frontend Components

### 14.1 `ReplacementPanel.tsx`

Responsibilities:

* Show replacement input.
* Require generated regex before enabling replacement.
* Allow empty string replacement.
* Show Apply Replacement button.
* Show loading state.
* Show errors.

Input placeholder:

```text
REDACTED
```

UX rule:

```text
Replacement value can be empty if the user wants to remove matches.
```

---

### 14.2 `ReplacementStatsCard.tsx`

Display:

* Checked rows
* Matched rows
* Total matches
* Replaced rows

Example:

```text
Checked rows: 50
Matched rows: 3
Total matches: 3
Replaced rows: 3
```

---

### 14.3 `ProcessedDataTable.tsx`

Responsibilities:

* Render processed preview.
* Use same table style as original preview.
* Clearly label it as processed data.
* Do not overwrite original preview table.

Recommended layout:

```text
Original Data Preview
Regex Generation Panel
Replacement Panel
Processed Data Preview
Replacement Stats
```

---

## 15. Frontend State Flow

`HomePage.tsx` should manage:

```ts
uploadResult
selectedColumn
regexResult
replacementValue
replaceResult
loading states
error states
```

Recommended state separation:

```ts
const [regexResult, setRegexResult] = useState<RegexGenerateResponse | null>(null);
const [replacementValue, setReplacementValue] = useState("REDACTED");
const [replaceResult, setReplaceResult] = useState<RegexReplaceResponse | null>(null);
const [replaceLoading, setReplaceLoading] = useState(false);
const [replaceError, setReplaceError] = useState<string | null>(null);
```

Important:

* If user uploads a new file, clear regex result and replacement result.
* If user changes selected column, clear regex result and replacement result.
* If user generates a new regex, clear previous replacement result.
* If replacement fails, keep generated regex visible.

---

## 16. UX Requirements

Minimum behavior:

1. Replacement panel is disabled until regex generation succeeds.
2. Replacement value input exists.
3. Empty replacement string is allowed.
4. Apply button shows loading state.
5. Processed table appears after successful replacement.
6. Stats appear after successful replacement.
7. Original table remains visible.
8. Backend errors render cleanly.
9. User can run replacement again with a different replacement value.
10. User can generate a new regex and then apply replacement again.

---

## 17. Backend Testing Plan

Mock or construct DataFrame/file fixtures.

Required tests:

### 17.1 Successful Email Redaction

Given CSV:

```csv
ID,Name,Email
1,John Doe,john.doe@example.com
2,Jane Smith,jane_smith@domain.com
3,Alice Brown,alice.brown@website.org
```

Request:

```json
{
  "target_column": "Email",
  "regex": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,7}\\b",
  "replacement": "REDACTED"
}
```

Expect:

```text
Email column values become REDACTED
matched_rows = 3
total_matches = 3
replaced_rows = 3
```

---

### 17.2 No Matches

Request uses valid regex but no value matches.

Expected behavior:

Option A:

```text
Return 200 with matched_rows = 0 and warning.
```

Option B:

```text
Return 400 with NO_MATCHES_FOUND.
```

Recommended:

Use **Option A**.

Reason:

No matches is not a system error. The user may be testing a pattern.

Response warning:

```json
"warnings": ["No matches were found in the selected column preview."]
```

---

### 17.3 Invalid Regex

Invalid regex:

```text
[
```

Expect:

```text
400 REGEX_COMPILE_ERROR
```

---

### 17.4 Unsafe Regex

Unsafe regex:

```text
(.+)+
```

Expect:

```text
400 REGEX_UNSAFE
```

---

### 17.5 Missing Column

Expect:

```text
400 COLUMN_NOT_FOUND
```

---

### 17.6 Missing Replacement Field

Expect:

```text
400 MISSING_REPLACEMENT
```

Note:

```json
"replacement": ""
```

should be valid.

---

### 17.7 Null Values

Input contains empty cells.

Expect:

```text
No backend crash.
Null target-column values become empty strings or remain JSON-safe.
```

---

## 18. Frontend Manual Testing Plan

Manual checks:

* [ ] Upload CSV.
* [ ] Generate regex for email addresses.
* [ ] Enter `REDACTED`.
* [ ] Apply replacement.
* [ ] Processed table shows redacted email values.
* [ ] Stats show correct counts.
* [ ] Original table remains visible.
* [ ] Change replacement value and apply again.
* [ ] Generate new regex and ensure old processed result clears.
* [ ] Invalid regex error displays cleanly if backend returns error.
* [ ] Empty replacement value is allowed.
* [ ] Uploading a new file clears old processed result.

---

## 19. Acceptance Criteria

Phase 4 is complete only when:

### Backend

* [ ] `POST /api/regex/replace/` exists.
* [ ] Endpoint accepts `file_id`, `target_column`, `regex`, and `replacement`.
* [ ] Backend loads the uploaded file by `file_id`.
* [ ] Backend validates target column.
* [ ] Backend validates regex.
* [ ] Backend applies replacement only to the selected column.
* [ ] Backend returns processed preview.
* [ ] Backend returns replacement statistics.
* [ ] Backend handles no-match cases safely.
* [ ] Backend tests cover successful replacement and failure cases.

### Frontend

* [ ] Replacement input appears after regex generation.
* [ ] Apply Replacement button works.
* [ ] Replacement loading state works.
* [ ] Processed table is displayed.
* [ ] Replacement stats are displayed.
* [ ] Original table remains visible.
* [ ] User-friendly errors are displayed.
* [ ] State resets correctly when file, column, or regex changes.

### Scope Control

* [ ] No deployment work.
* [ ] No authentication.
* [ ] No optional LLM transformations.
* [ ] No unrelated UI redesign.
* [ ] No secrets committed.

---

## 20. Suggested Commit Plan

```text
commit 1: feat: add regex replacement API schema
commit 2: feat: add replacement processor service
commit 3: feat: add regex replace endpoint
commit 4: test: add backend replacement tests
commit 5: feat: add frontend replacement API types
commit 6: feat: add replacement input panel
commit 7: feat: add processed table and replacement stats
commit 8: chore: update README and phase docs
```

---

## 21. Risk Register

| Risk                                                 | Impact                       | Mitigation                                        |
| ---------------------------------------------------- | ---------------------------- | ------------------------------------------------- |
| Regex replacement mutates original data unexpectedly | confusing UX                 | copy DataFrame before processing                  |
| Empty replacement rejected incorrectly               | cannot remove matched text   | allow empty string but require field existence    |
| No-match case treated as crash                       | poor UX                      | return 200 with warning                           |
| JSON serialization fails                             | frontend crash               | reuse DataFrame normalization                     |
| Unsafe regex slows backend                           | performance issue            | reuse validator and preview limits                |
| State becomes inconsistent on frontend               | wrong processed result shown | clear processed state on file/column/regex change |

---

## 22. Phase Exit Decision

Phase 4 can exit only if:

```text
A user can upload a CSV/XLSX file, generate a regex, enter a replacement value, apply the replacement to a selected column, and see the processed table plus replacement statistics in the frontend.
```

If this is not true, do not proceed to deployment, download, or optional transformations.

````

---



## 关键判断

Phase 4 不要再让 LLM 参与。
流程应该是：

```text
LLM generates regex in Phase 3
Backend validates regex
User confirms replacement value
Backend executes deterministic replacement in Phase 4
```

这能保证系统可解释、可测试、可复现。下一步等 Phase 4 跑通后，再做 **Phase 5：download processed file + final polish + README**。
