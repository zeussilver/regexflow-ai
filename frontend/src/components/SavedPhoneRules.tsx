import { useEffect, useState } from "react";
import {
  executeRule,
  listExecutions,
  listRules,
  PhoneRuleVersion,
  previewRule,
  RuleExecution,
  ruleError,
  RuleParameters,
  RulePreview,
  RuleResult,
  saveRule,
} from "../api/rules";
import type {
  PhoneNormalizationResponse,
  PhoneTargetFormat,
} from "../types/transformations";
import ErrorMessage from "./ErrorMessage";
import TransformationResultTable from "./TransformationResultTable";

const formats: PhoneTargetFormat[] = [
  "E164",
  "INTERNATIONAL",
  "NATIONAL",
  "RFC3966",
];

export default function SavedPhoneRules({
  fileId,
  successfulRule,
}: {
  fileId?: string;
  successfulRule: PhoneNormalizationResponse | null;
}) {
  const [rules, setRules] = useState<PhoneRuleVersion[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [name, setName] = useState("Customer phone normalisation — AU → E.164");
  const [draft, setDraft] = useState<RuleParameters | null>(null);
  const [preview, setPreview] = useState<RulePreview | null>(null);
  const [result, setResult] = useState<RuleResult | null>(null);
  const [history, setHistory] = useState<RuleExecution[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const selected = rules.find((rule) => rule.version_id === selectedId);

  useEffect(() => {
    let active = true;
    listRules()
      .then((data) => {
        if (active) setRules(data);
      })
      .catch((err) => {
        if (active) setError(ruleError(err));
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    let active = true;
    setHistory([]);
    if (selected)
      listExecutions(selected.rule_id)
        .then((data) => {
          if (active) setHistory(data);
        })
        .catch((err) => {
          if (active) setError(ruleError(err));
        });
    return () => {
      active = false;
    };
  }, [selected?.rule_id]);

  function select(rule?: PhoneRuleVersion) {
    setSelectedId(rule?.version_id ?? "");
    setDraft(
      rule
        ? {
            name: rule.name,
            target_column: rule.target_column,
            default_region: rule.default_region,
            target_format: rule.target_format,
            preserve_invalid: rule.preserve_invalid,
          }
        : null,
    );
    setPreview(null);
    setResult(null);
    setError(null);
    setNotice("");
  }
  async function save(parameters: RuleParameters, source?: string) {
    setBusy(true);
    setError(null);
    setNotice("");
    try {
      const saved = await saveRule(parameters, source);
      setRules(await listRules());
      select(saved);
      setNotice(`Saved ${saved.name} v${saved.version}`);
    } catch (err) {
      setError(ruleError(err));
    } finally {
      setBusy(false);
    }
  }
  async function makePreview() {
    if (!selected || !fileId) return;
    setBusy(true);
    setError(null);
    setPreview(null);
    setResult(null);
    try {
      setPreview(await previewRule(selected.version_id, fileId));
    } catch (err) {
      setError(ruleError(err));
    } finally {
      setBusy(false);
    }
  }
  async function execute() {
    if (!selected || !preview) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(
        await executeRule(selected.version_id, preview.confirmation_token),
      );
    } catch (err) {
      setError(ruleError(err));
    } finally {
      setPreview(null);
      try {
        setHistory(await listExecutions(selected.rule_id));
      } catch (err) {
        setError(ruleError(err));
      }
      setBusy(false);
    }
  }

  return (
    <section className="phone-panel" aria-labelledby="saved-rules-heading">
      <h2 id="saved-rules-heading">Saved phone rules</h2>
      <p>
        Shared demo rules and execution history are visible to everyone. Reusing
        a saved version does not call a model.
      </p>
      <fieldset disabled={busy} className="saved-rule-controls">
        {successfulRule && successfulRule.target_columns.length === 1 && (
          <div>
            <h3>Save the validated phone rule</h3>
            <p>
              {successfulRule.target_columns[0]} ·{" "}
              {successfulRule.rule.default_region} ·{" "}
              {successfulRule.rule.target_format} ·{" "}
              {successfulRule.rule.preserve_invalid
                ? "Keep invalid values"
                : "Clear invalid values"}
            </p>
            <label className="field-block">
              Rule name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={160}
              />
            </label>
            <button
              type="button"
              disabled={!name.trim()}
              onClick={() =>
                save({
                  name: name.trim(),
                  target_column: successfulRule.target_columns[0],
                  default_region: successfulRule.rule.default_region,
                  target_format: successfulRule.rule.target_format,
                  preserve_invalid: successfulRule.rule.preserve_invalid,
                })
              }
            >
              Save phone rule
            </button>
          </div>
        )}
        <label className="field-block">
          Saved rule version
          <select
            value={selectedId}
            onChange={(e) =>
              select(rules.find((rule) => rule.version_id === e.target.value))
            }
          >
            <option value="">Choose a saved version</option>
            {rules.map((rule) => (
              <option key={rule.version_id} value={rule.version_id}>
                {rule.name} — v{rule.version}
              </option>
            ))}
          </select>
        </label>
        {selected && (
          <>
            <p>
              Selected v{selected.version}: {selected.target_column} ·{" "}
              {selected.default_region} · {selected.target_format} ·{" "}
              {selected.preserve_invalid
                ? "Keep invalid values"
                : "Clear invalid values"}
            </p>
            <button type="button" disabled={!fileId} onClick={makePreview}>
              Preview saved rule
            </button>
            {!fileId && (
              <p>
                Upload a file containing {selected.target_column} to preview
                this version.
              </p>
            )}
            {draft && (
              <details>
                <summary>Create a new immutable version</summary>
                <p>
                  These parameters create a new version. The selected version
                  stays unchanged.
                </p>
                <label className="field-block">
                  Version name
                  <input
                    value={draft.name}
                    maxLength={160}
                    onChange={(e) =>
                      setDraft({ ...draft, name: e.target.value })
                    }
                  />
                </label>
                <label className="field-block">
                  Version target column
                  <input
                    value={draft.target_column}
                    onChange={(e) =>
                      setDraft({ ...draft, target_column: e.target.value })
                    }
                  />
                </label>
                <label className="field-block">
                  Version region
                  <input
                    value={draft.default_region}
                    maxLength={2}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        default_region: e.target.value.toUpperCase(),
                      })
                    }
                  />
                </label>
                <label className="field-block">
                  Version format
                  <select
                    value={draft.target_format}
                    onChange={(e) =>
                      setDraft({
                        ...draft,
                        target_format: e.target.value as PhoneTargetFormat,
                      })
                    }
                  >
                    {formats.map((format) => (
                      <option key={format}>{format}</option>
                    ))}
                  </select>
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={draft.preserve_invalid}
                    onChange={(e) =>
                      setDraft({ ...draft, preserve_invalid: e.target.checked })
                    }
                  />
                  Keep invalid phone values
                </label>
                <button
                  type="button"
                  onClick={() => save(draft, selected.version_id)}
                >
                  Save new version
                </button>
              </details>
            )}
          </>
        )}
        {preview && selected && (
          <div>
            <h3>Confirm phone preview</h3>
            <p>
              {preview.row_count} rows checked; {preview.changed_rows} rows will
              change. Showing at most 50 rows. Confirmation expires in 15
              minutes.
            </p>
            <div className="table-shell">
              <table aria-label="Saved rule before and after">
                <thead>
                  <tr>
                    <th>Row</th>
                    <th>Before</th>
                    <th>After</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.before_preview.map((row, i) => (
                    <tr key={i}>
                      <td>{i + 1}</td>
                      <td>{String(row[selected.target_column] ?? "")}</td>
                      <td>
                        {String(
                          preview.processed_preview[i][
                            selected.target_column
                          ] ?? "",
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              Invalid values: {preview.stats.invalid_cells}.{" "}
              {preview.warnings.join(" ")}
            </p>
            <button type="button" onClick={execute}>
              Confirm and execute
            </button>
          </div>
        )}
      </fieldset>
      {busy && <p role="status">Working…</p>}
      {notice && <p role="status">{notice}</p>}
      <ErrorMessage message={error} />
      {result && (
        <p role="status">
          Execution {result.execution.status}: {result.execution.changed_rows}{" "}
          rows changed.
        </p>
      )}
      <TransformationResultTable result={result} />
      {selected && (
        <div>
          <h3>Recent executions</h3>
          <p>
            Latest 20 runs for this rule group. A running entry has not
            completed.
          </p>
          <ul aria-label="Execution history">
            {history.map((entry) => (
              <li key={entry.id}>
                {entry.status} · {new Date(entry.started_at).toLocaleString()} ·{" "}
                {entry.changed_rows === null
                  ? "Change count unavailable"
                  : `${entry.changed_rows} rows changed`}
                {entry.error_code && ` · ${entry.error_code}`}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
