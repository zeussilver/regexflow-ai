import type { PreviewRow } from "./files";

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
  flags: string[];
  explanation: string;
  target_column: string;
  match_preview: MatchPreview;
  warnings: string[];
}

export interface RegexReplaceRequest {
  file_id: string;
  target_column: string;
  regex: string;
  flags?: string[];
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
  processed_file_id: string;
  target_column: string;
  regex: string;
  flags: string[];
  replacement: string;
  columns: string[];
  row_count: number;
  preview_limit: number;
  processed_preview: PreviewRow[];
  stats: ReplacementStats;
  warnings: string[];
}

export interface RegexApiErrorPayload {
  error: {
    code: string;
    message: string;
  };
}

export class RegexApiError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "RegexApiError";
    this.code = code;
  }
}
