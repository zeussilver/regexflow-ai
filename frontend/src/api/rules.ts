import axios from "axios";
import { apiClient } from "./client";
import type {
  PhoneNormalizationResponse,
  PhoneTargetFormat,
} from "../types/transformations";
import type { PreviewRow } from "../types/files";

export interface RuleParameters {
  name: string;
  target_column: string;
  default_region: string;
  target_format: PhoneTargetFormat;
  preserve_invalid: boolean;
}
export interface PhoneRuleVersion extends RuleParameters {
  rule_id: string;
  version_id: string;
  version: number;
  created_at: string;
}
export interface RuleExecution {
  id: string;
  rule_version_id: string;
  input_file_id: string;
  output_file_id: string | null;
  status: "running" | "succeeded" | "failed";
  changed_rows: number | null;
  started_at: string;
  finished_at: string | null;
  error_code: string;
}
export interface RulePreview extends PhoneNormalizationResponse {
  before_preview: PreviewRow[];
  changed_rows: number;
  confirmation_token: string;
  expires_in: number;
}
export interface RuleResult extends PhoneNormalizationResponse {
  execution: RuleExecution;
}
export const listRules = async () =>
  (await apiClient.get<{ rules: PhoneRuleVersion[] }>("/rules/")).data.rules;
export const saveRule = async (parameters: RuleParameters, source?: string) =>
  (
    await apiClient.post<PhoneRuleVersion>(
      source ? `/rules/${source}/versions/` : "/rules/",
      parameters,
    )
  ).data;
export const previewRule = async (version: string, file: string) =>
  (
    await apiClient.post<RulePreview>(`/rules/${version}/preview/`, {
      file_id: file,
    })
  ).data;
export const executeRule = async (version: string, token: string) =>
  (
    await apiClient.post<RuleResult>(`/rules/${version}/execute/`, {
      confirmation_token: token,
    })
  ).data;
export const listExecutions = async (group: string) =>
  (
    await apiClient.get<{ executions: RuleExecution[] }>("/rule-executions/", {
      params: { rule_id: group },
    })
  ).data.executions;
export function ruleError(error: unknown): string {
  if (axios.isAxiosError(error) && error.response?.data?.error?.message)
    return error.response.data.error.message;
  return "The rule request failed. Check the backend and try again.";
}
