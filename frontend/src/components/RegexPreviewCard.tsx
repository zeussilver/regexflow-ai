import { RegexGenerateResponse } from "../types/regex";

interface RegexPreviewCardProps {
  result: RegexGenerateResponse | null;
}

export default function RegexPreviewCard({ result }: RegexPreviewCardProps) {
  if (!result) {
    return null;
  }

  function handleCopy() {
    if (!result) {
      return;
    }

    void navigator.clipboard?.writeText(result.regex);
  }

  return (
    <section className="regex-result-panel">
      <div className="regex-result-header">
        <div>
          <p className="eyebrow">Generated Regex</p>
          <h2>{result.target_column}</h2>
        </div>
        <button className="copy-button" type="button" onClick={handleCopy}>
          Copy
        </button>
      </div>

      <code className="regex-code">{result.regex}</code>

      <p className="regex-explanation">{result.explanation}</p>

      <dl className="stats regex-stats">
        <div>
          <dt>Checked</dt>
          <dd>{result.match_preview.checked_rows.toLocaleString()}</dd>
        </div>
        <div>
          <dt>Matched</dt>
          <dd>{result.match_preview.matched_rows.toLocaleString()}</dd>
        </div>
      </dl>

      {result.match_preview.examples.length > 0 ? (
        <div className="match-examples">
          <h3>Example Matches</h3>
          <ul>
            {result.match_preview.examples.map((example) => (
              <li key={`${example.row_index}-${example.value}`}>
                <span className="row-index">Row {example.row_index + 1}</span>
                <span className="match-value">{example.value}</span>
                <span className="match-list">{example.matches.join(", ")}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="no-matches">No matches found in the first checked rows.</p>
      )}

      {result.warnings.length > 0 ? (
        <ul className="warning-list">
          {result.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
