import { FormEvent } from "react";

import { PiiReplacementStrategy, PiiType } from "../types/transformations";

interface PiiRedactionPanelProps {
  columns: string[];
  hasUploadedFile: boolean;
  isLoading: boolean;
  replacementStrategy: PiiReplacementStrategy;
  selectedPiiTypes: PiiType[];
  selectedTargetColumns: string[];
  onApply: () => void;
  onPiiTypesChange: (piiTypes: PiiType[]) => void;
  onReplacementStrategyChange: (strategy: PiiReplacementStrategy) => void;
  onTargetColumnsChange: (columns: string[]) => void;
}

const piiTypes: Array<{ value: PiiType; label: string }> = [
  { value: "email", label: "Email" },
  { value: "phone", label: "Phone" },
  { value: "credit_card", label: "Credit card" },
  { value: "url", label: "URL" },
];

const replacementStrategies: Array<{ value: PiiReplacementStrategy; label: string }> = [
  { value: "typed_placeholders", label: "Typed placeholders" },
  { value: "generic_redacted", label: "Generic redacted" },
];

export default function PiiRedactionPanel({
  columns,
  hasUploadedFile,
  isLoading,
  replacementStrategy,
  selectedPiiTypes,
  selectedTargetColumns,
  onApply,
  onPiiTypesChange,
  onReplacementStrategyChange,
  onTargetColumnsChange,
}: PiiRedactionPanelProps) {
  const isDisabled = !hasUploadedFile || isLoading;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onApply();
  }

  function handleTargetColumnToggle(column: string, checked: boolean) {
    const nextColumns = checked
      ? [...selectedTargetColumns, column]
      : selectedTargetColumns.filter((selectedColumn) => selectedColumn !== column);

    onTargetColumnsChange(nextColumns);
  }

  function handlePiiTypeToggle(piiType: PiiType, checked: boolean) {
    const nextTypes = checked
      ? [...selectedPiiTypes, piiType]
      : selectedPiiTypes.filter((selectedType) => selectedType !== piiType);

    onPiiTypesChange(nextTypes);
  }

  return (
    <section className="pii-panel">
      <div className="transformation-panel-header">
        <div>
          <p className="eyebrow">PII Redaction Assistant</p>
          <h2>Redact Sensitive Values</h2>
        </div>
        <span className="phase-badge">Optional</span>
      </div>

      <form className="transformation-form pii-form" onSubmit={handleSubmit}>
        <fieldset className="checkbox-fieldset" disabled={isDisabled}>
          <legend>Target columns</legend>
          <div className="checkbox-grid">
            {columns.map((column) => (
              <label className="checkbox-option" key={column}>
                <input
                  type="checkbox"
                  checked={selectedTargetColumns.includes(column)}
                  onChange={(event) => handleTargetColumnToggle(column, event.target.checked)}
                />
                <span>{column}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="checkbox-fieldset" disabled={isDisabled}>
          <legend>PII types</legend>
          <div className="checkbox-grid compact-checkbox-grid">
            {piiTypes.map((piiType) => (
              <label className="checkbox-option" key={piiType.value}>
                <input
                  type="checkbox"
                  checked={selectedPiiTypes.includes(piiType.value)}
                  onChange={(event) => handlePiiTypeToggle(piiType.value, event.target.checked)}
                />
                <span>{piiType.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="transformation-action-row">
          <label className="field-block" htmlFor="pii-replacement-strategy">
            <span>Replacement strategy</span>
            <select
              id="pii-replacement-strategy"
              value={replacementStrategy}
              disabled={isDisabled}
              onChange={(event) =>
                onReplacementStrategyChange(event.target.value as PiiReplacementStrategy)
              }
            >
              {replacementStrategies.map((strategy) => (
                <option key={strategy.value} value={strategy.value}>
                  {strategy.label}
                </option>
              ))}
            </select>
          </label>

          <button
            className="transformation-button"
            type="submit"
            disabled={!hasUploadedFile || isLoading}
          >
            {isLoading ? "Applying" : "Apply Redaction"}
          </button>
        </div>
      </form>
    </section>
  );
}
