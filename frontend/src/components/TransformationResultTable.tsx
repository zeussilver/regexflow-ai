import { PreviewCellValue } from "../types/files";
import { TransformationResponse } from "../types/transformations";

interface TransformationResultTableProps {
  result: TransformationResponse | null;
}

export default function TransformationResultTable({ result }: TransformationResultTableProps) {
  if (!result) {
    return null;
  }

  const resultId = result.processed_file_id ?? `${result.file_id}-${result.transformation}`;

  return (
    <section className="preview-panel processed-panel transformation-result-panel">
      <div className="preview-header">
        <div>
          <p className="eyebrow">Transformation Preview</p>
          <h2>{result.transformation === "pii_redaction" ? "PII Redaction" : "Phone Normalization"}</h2>
        </div>
        <dl className="stats">
          <div>
            <dt>Rows</dt>
            <dd>{result.row_count.toLocaleString()}</dd>
          </div>
          <div>
            <dt>Shown</dt>
            <dd>{result.processed_preview.length.toLocaleString()}</dd>
          </div>
        </dl>
      </div>

      <div className="table-shell">
        <table>
          <thead>
            <tr>
              {result.columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.processed_preview.map((row, rowIndex) => (
              <tr key={`${resultId}-${rowIndex}`}>
                {result.columns.map((column) => (
                  <td key={`${rowIndex}-${column}`}>{formatCell(row[column])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {result.warnings.length > 0 ? (
        <ul className="warning-list processed-warning-list">
          {result.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function formatCell(value: PreviewCellValue): string {
  if (value === null || value === undefined || value === "") {
    return " ";
  }

  return String(value);
}
