export type IssueSeverity = "error" | "warning";

export interface DataHolder {
  key: string;
  name: string;
  product_base_uri: string;
}

export interface CheckRule {
  rule_id: string;
  severity: IssueSeverity;
  title: string;
}

export interface RuleCount extends CheckRule {
  count: number;
}

export interface ProductCheckRun {
  id: string;
  source_type: "upload" | "live";
  source_label: string;
  holder_key: string;
  list_version: string;
  detail_version: string;
  ruleset_version: string;
  reference_time: string;
  product_count: number;
  detail_count: number;
  products_with_errors: number;
  error_count: number;
  warning_count: number;
  report_file_id: string | null;
  compared_with: string | null;
  compared_with_time: string | null;
  created_at: string;
}

export interface ProductIssue {
  rule_id: string;
  severity: IssueSeverity;
  product_index: number;
  product_id: string;
  product_name: string;
  field: string;
  message: string;
  value: string;
}

export interface ProductCheckResult {
  run: ProductCheckRun;
  by_rule: RuleCount[];
  issues: ProductIssue[];
  issues_truncated: boolean;
}
