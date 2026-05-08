import { TransformationResponse } from "../types/transformations";

interface TransformationStatsCardProps {
  result: TransformationResponse | null;
}

export default function TransformationStatsCard({ result }: TransformationStatsCardProps) {
  if (!result) {
    return null;
  }

  if (result.transformation === "pii_redaction") {
    const byTypeEntries = Object.entries(result.stats.by_type);

    return (
      <section className="transformation-stats-panel">
        <div className="transformation-stats-header">
          <div>
            <p className="eyebrow">Transformation Result</p>
            <h2>PII Stats</h2>
          </div>
        </div>

        <dl className="stats transformation-stats">
          <div>
            <dt>Checked</dt>
            <dd>{result.stats.checked_cells.toLocaleString()}</dd>
          </div>
          <div>
            <dt>Changed</dt>
            <dd>{result.stats.changed_cells.toLocaleString()}</dd>
          </div>
          <div>
            <dt>Replacements</dt>
            <dd>{result.stats.total_replacements.toLocaleString()}</dd>
          </div>
        </dl>

        {byTypeEntries.length > 0 ? (
          <div className="transformation-type-stats">
            <h3>By Type</h3>
            <ul className="transformation-type-list">
              {byTypeEntries.map(([type, stats]) => (
                <li key={type}>
                  <span className="transformation-type-name">{formatType(type)}</span>
                  <span>Matches {stats.matches.toLocaleString()}</span>
                  <span>Changed {stats.changed_cells.toLocaleString()}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>
    );
  }

  return (
    <section className="transformation-stats-panel">
      <div className="transformation-stats-header">
        <div>
          <p className="eyebrow">Transformation Result</p>
          <h2>Phone Stats</h2>
        </div>
      </div>

      <dl className="stats transformation-stats">
        <div>
          <dt>Checked</dt>
          <dd>{result.stats.checked_cells.toLocaleString()}</dd>
        </div>
        <div>
          <dt>Normalized</dt>
          <dd>{result.stats.normalized_cells.toLocaleString()}</dd>
        </div>
        <div>
          <dt>Invalid</dt>
          <dd>{result.stats.invalid_cells.toLocaleString()}</dd>
        </div>
        <div>
          <dt>Unchanged</dt>
          <dd>{result.stats.unchanged_cells.toLocaleString()}</dd>
        </div>
      </dl>
    </section>
  );
}

function formatType(type: string): string {
  return type.replace("_", " ");
}
