import { PreviewCellValue } from "../types/files";
import { RegexReplaceResponse } from "../types/regex";
import ProcessedDownloadLink from "./ProcessedDownloadLink";

interface ProcessedDataTableProps {
  result: RegexReplaceResponse | null;
}

export default function ProcessedDataTable({ result }: ProcessedDataTableProps) {
  if (!result) {
    return null;
  }

  return (
    <section className="preview-panel processed-panel">
      <div className="preview-header">
        <div>
          <p className="eyebrow">Processed Preview</p>
          <h2>{result.target_column}</h2>
        </div>
        <div className="preview-header-actions">
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
          <ProcessedDownloadLink processedFileId={result.processed_file_id} />
        </div>
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
              <tr key={`${result.processed_file_id}-${rowIndex}`}>
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
