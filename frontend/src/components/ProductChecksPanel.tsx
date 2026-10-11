import { FormEvent, useEffect, useState } from "react";
import {
  checkLiveHolder,
  checkUploadedProducts,
  getProductCheck,
  listCheckRules,
  listHolders,
  listProductChecks,
  productCheckError,
} from "../api/productChecks";
import type {
  CheckRule,
  DataHolder,
  IssueSeverity,
  ProductCheckResult,
  ProductCheckRun,
} from "../types/productChecks";
import ErrorMessage from "./ErrorMessage";
import ProcessedDownloadLink from "./ProcessedDownloadLink";

type Source = "live" | "upload";

export default function ProductChecksPanel() {
  const [holders, setHolders] = useState<DataHolder[]>([]);
  const [rules, setRules] = useState<CheckRule[]>([]);
  const [runs, setRuns] = useState<ProductCheckRun[]>([]);
  const [source, setSource] = useState<Source>("live");
  const [holder, setHolder] = useState("");
  const [includeDetails, setIncludeDetails] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ProductCheckResult | null>(null);
  const [severity, setSeverity] = useState<IssueSeverity | "all">("all");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const holderName = holders.find((item) => item.key === holder)?.name ?? holder;
  const ready = source === "live" ? Boolean(holder) : Boolean(file);

  useEffect(() => {
    let active = true;
    Promise.all([listHolders(), listCheckRules(), listProductChecks()])
      .then(([holderList, catalogue, recent]) => {
        if (!active) return;
        setHolders(holderList);
        setHolder((current) => current || holderList[0]?.key || "");
        setRules(catalogue.rules);
        setRuns(recent);
      })
      .catch((err) => {
        if (active) setError(productCheckError(err));
      });
    return () => {
      active = false;
    };
  }, []);

  async function load(task: () => Promise<ProductCheckResult>) {
    setBusy(true);
    setError(null);
    setResult(null);
    setSeverity("all");
    try {
      setResult(await task());
      setRuns(await listProductChecks());
    } catch (err) {
      setError(productCheckError(err));
    } finally {
      setBusy(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (source === "live" && holder) {
      load(() => checkLiveHolder(holder, includeDetails));
    } else if (source === "upload" && file) {
      load(() => checkUploadedProducts(file));
    }
  }

  return (
    <section className="product-checks-panel" aria-labelledby="product-checks-heading">
      <p className="eyebrow">Open Banking data quality</p>
      <h2 id="product-checks-heading">CDR product data checks</h2>
      <p className="product-checks-intro">
        Check Consumer Data Right banking product reference data against{" "}
        {rules.length} deterministic rules based on the Consumer Data Standards.
        Live checks call a bank&apos;s public Get Products and Get Product Detail
        APIs; uploads accept either response as JSON.
      </p>

      <form onSubmit={handleSubmit}>
        <fieldset className="product-check-form" disabled={busy}>
          <legend>Source</legend>
          <div className="product-check-sources">
            {(["live", "upload"] as const).map((option) => (
              <label key={option} className="checkbox-option">
                <input
                  type="radio"
                  name="product-check-source"
                  checked={source === option}
                  onChange={() => setSource(option)}
                />
                <span>{option === "live" ? "Live data holder" : "Upload JSON"}</span>
              </label>
            ))}
          </div>
          {source === "live" ? (
            <>
              <label className="field-block">
                Data holder
                <select value={holder} onChange={(e) => setHolder(e.target.value)}>
                  {holders.map((item) => (
                    <option key={item.key} value={item.key}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="checkbox-option">
                <input
                  type="checkbox"
                  checked={includeDetails}
                  onChange={(e) => setIncludeDetails(e.target.checked)}
                />
                <span>Include product details (rates and fees)</span>
              </label>
            </>
          ) : (
            <label className="field-block">
              CDR products JSON
              <input
                type="file"
                accept=".json,application/json"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </label>
          )}
          <button
            className="action-button"
            type="submit"
            data-action-state={busy ? "loading" : ready ? "ready" : "locked"}
            disabled={!ready}
          >
            {busy ? "Checking" : "Run checks"}
          </button>
        </fieldset>
      </form>
      {busy && (
        <p role="status">
          {source === "live"
            ? `Checking ${holderName}. Product details can take up to a minute.`
            : "Checking the uploaded products."}
        </p>
      )}
      <ErrorMessage message={error} />

      {result && (
        <CheckResult result={result} severity={severity} onSeverityChange={setSeverity} />
      )}

      {runs.length > 0 && (
        <div className="product-check-history">
          <h3>Recent checks</h3>
          <div className="table-shell">
            <table aria-label="Recent checks">
              <thead>
                <tr>
                  <th>Checked</th>
                  <th>Source</th>
                  <th>Products</th>
                  <th>Errors</th>
                  <th>Warnings</th>
                  <th>Report</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id}>
                    <td>{new Date(run.created_at).toLocaleString()}</td>
                    <td>{run.source_label}</td>
                    <td>{run.product_count}</td>
                    <td>{run.error_count}</td>
                    <td>{run.warning_count}</td>
                    <td>
                      <button
                        className="compact-button"
                        type="button"
                        disabled={busy}
                        onClick={() => load(() => getProductCheck(run.id))}
                      >
                        Open
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {rules.length > 0 && (
        <details className="product-check-rules">
          <summary>What the {rules.length} rules check</summary>
          <ul>
            {rules.map((rule) => (
              <li key={rule.rule_id}>
                <strong>{rule.rule_id}</strong> <SeverityLabel severity={rule.severity} />{" "}
                {rule.title}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

function CheckResult({
  result,
  severity,
  onSeverityChange,
}: {
  result: ProductCheckResult;
  severity: IssueSeverity | "all";
  onSeverityChange: (severity: IssueSeverity | "all") => void;
}) {
  const { run } = result;
  const issues = result.issues.filter(
    (issue) => severity === "all" || issue.severity === severity,
  );
  const versions = [
    run.list_version && `Get Products v${run.list_version}`,
    run.detail_version && `Get Product Detail v${run.detail_version}`,
  ].filter(Boolean);

  return (
    <div className="product-check-result">
      <div className="preview-header">
        <div>
          <p className="eyebrow">Check result</p>
          <h3>{run.source_label}</h3>
        </div>
        <dl className="stats">
          <div>
            <dt>Products</dt>
            <dd>{run.product_count}</dd>
          </div>
          <div>
            <dt>With errors</dt>
            <dd>{run.products_with_errors}</dd>
          </div>
          <div>
            <dt>Errors</dt>
            <dd>{run.error_count}</dd>
          </div>
          <div>
            <dt>Warnings</dt>
            <dd>{run.warning_count}</dd>
          </div>
        </dl>
      </div>
      <p className="product-check-meta">
        {versions.length > 0 && `${versions.join(" · ")} · `}
        Details checked for {run.detail_count} of {run.product_count} products ·
        Reference time {new Date(run.reference_time).toLocaleString()} · Ruleset{" "}
        {run.ruleset_version}
        {run.compared_with_time &&
          ` · Compared with the check at ${new Date(run.compared_with_time).toLocaleString()}`}
      </p>
      {run.report_file_id && (
        <ProcessedDownloadLink processedFileId={run.report_file_id} />
      )}

      {result.by_rule.length === 0 ? (
        <p role="status">No issues found.</p>
      ) : (
        <>
          <div className="table-shell product-check-table">
            <table aria-label="Issues by rule">
              <thead>
                <tr>
                  <th>Rule</th>
                  <th>Severity</th>
                  <th>Check</th>
                  <th>Issues</th>
                </tr>
              </thead>
              <tbody>
                {result.by_rule.map((rule) => (
                  <tr key={rule.rule_id}>
                    <td>{rule.rule_id}</td>
                    <td>
                      <SeverityLabel severity={rule.severity} />
                    </td>
                    <td>{rule.title}</td>
                    <td>{rule.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <label className="field-block product-check-filter">
            Show
            <select
              value={severity}
              onChange={(e) => onSeverityChange(e.target.value as IssueSeverity | "all")}
            >
              <option value="all">All issues</option>
              <option value="error">Errors</option>
              <option value="warning">Warnings</option>
            </select>
          </label>
          <div className="table-shell product-check-table">
            <table aria-label="Product issues" className="issues-table">
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Rule</th>
                  <th>Product</th>
                  <th>Field</th>
                  <th>Message</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {issues.map((issue, index) => (
                  <tr key={`${issue.rule_id}-${issue.product_index}-${issue.field}-${index}`}>
                    <td>
                      <SeverityLabel severity={issue.severity} />
                    </td>
                    <td>{issue.rule_id}</td>
                    <td>{issue.product_name || issue.product_id || `#${issue.product_index + 1}`}</td>
                    <td>{issue.field}</td>
                    <td>{issue.message}</td>
                    <td title={issue.value}>{issue.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {result.issues_truncated && (
            <p>
              Showing the first {result.issues.length} issues. Download the CSV for
              all {run.error_count + run.warning_count}.
            </p>
          )}
        </>
      )}
    </div>
  );
}

function SeverityLabel({ severity }: { severity: IssueSeverity }) {
  return <span className={`severity-${severity}`}>{severity}</span>;
}
