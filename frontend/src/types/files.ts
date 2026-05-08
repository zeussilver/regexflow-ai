export type PreviewCellValue = string | number | boolean | null;

export type PreviewRow = Record<string, PreviewCellValue>;

export interface FileUploadResponse {
  file_id: string;
  filename: string;
  columns: string[];
  row_count: number;
  preview_rows: PreviewRow[];
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
  };
}

export class UploadApiError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "UploadApiError";
    this.code = code;
  }
}
