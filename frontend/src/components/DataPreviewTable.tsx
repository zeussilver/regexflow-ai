import { FileUploadResponse, PreviewCellValue } from "../types/files";

interface DataPreviewTableProps {
  data: FileUploadResponse | null;
}

export default function DataPreviewTable({ data }: DataPreviewTableProps) {
  if (!data) {
    return (
      <section className="preview-panel preview-empty">
        <p className="eyebrow">Preview</p>
        <h2>No file loaded</h2>
      </section>
    );
  }

  return (
    <section className="preview-panel">
      <div className="preview-header">
        <div>
          <p className="eyebrow">Preview</p>
          <h2>{data.filename}</h2>
        </div>
        <dl className="stats">
          <div>
            <dt>Rows</dt>
            <dd>{data.row_count.toLocaleString()}</dd>
          </div>
          <div>
            <dt>Columns</dt>
            <dd>{data.columns.length.toLocaleString()}</dd>
          </div>
        </dl>
      </div>

      <div className="table-shell">
        <table>
          <thead>
            <tr>
              {data.columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.preview_rows.map((row, rowIndex) => (
              <tr key={`${data.file_id}-${rowIndex}`}>
                {data.columns.map((column) => (
                  <td key={`${rowIndex}-${column}`}>{formatCell(row[column])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatCell(value: PreviewCellValue): string {
  if (value === null || value === undefined || value === "") {
    return " ";
  }

  return String(value);
}
