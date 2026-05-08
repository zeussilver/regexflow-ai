import type { PreviewRow } from "./files";

export type PiiType = "email" | "phone" | "credit_card" | "url";

export type PiiReplacementStrategy = "typed_placeholders" | "generic_redacted";

export type PhoneTargetFormat = "E164" | "INTERNATIONAL" | "NATIONAL" | "RFC3966";

export type TransformationMode = "pii_redaction" | "phone_normalization";

export interface PiiRedactionRequest {
  file_id: string;
  target_columns?: string[];
  pii_types: PiiType[];
  replacement_strategy: PiiReplacementStrategy;
}

export interface PiiTypeStats {
  matches: number;
  changed_cells: number;
}

export interface PiiRedactionStats {
  checked_cells: number;
  changed_cells: number;
  total_replacements: number;
  by_type: Record<string, PiiTypeStats>;
}

export interface PiiRedactionResponse {
  file_id: string;
  processed_file_id?: string;
  transformation: "pii_redaction";
  columns: string[];
  row_count: number;
  preview_limit: number;
  processed_preview: PreviewRow[];
  stats: PiiRedactionStats;
  warnings: string[];
}

export interface PhoneNormalizationRequest {
  file_id: string;
  target_columns: string[];
  natural_language: string;
  default_region: string;
  target_format: PhoneTargetFormat;
}

export interface PhoneNormalizationRule {
  transformation_type: "phone_normalization";
  target_format: PhoneTargetFormat;
  default_region: string;
  preserve_invalid: boolean;
  explanation: string;
}

export interface PhoneNormalizationStats {
  checked_cells: number;
  normalized_cells: number;
  invalid_cells: number;
  unchanged_cells: number;
}

export interface PhoneNormalizationResponse {
  file_id: string;
  processed_file_id?: string;
  transformation: "phone_normalization";
  rule: PhoneNormalizationRule;
  columns: string[];
  row_count: number;
  preview_limit: number;
  processed_preview: PreviewRow[];
  stats: PhoneNormalizationStats;
  warnings: string[];
}

export type TransformationResponse = PiiRedactionResponse | PhoneNormalizationResponse;

export interface TransformationApiErrorPayload {
  error: {
    code: string;
    message: string;
  };
}

export class TransformationApiError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "TransformationApiError";
    this.code = code;
  }
}
