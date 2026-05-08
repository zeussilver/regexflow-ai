import { FormEvent } from "react";

interface ReplacementPanelProps {
  replacementValue: string;
  isLoading: boolean;
  onApply: () => void;
  onReplacementChange: (value: string) => void;
}

export default function ReplacementPanel({
  replacementValue,
  isLoading,
  onApply,
  onReplacementChange,
}: ReplacementPanelProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onApply();
  }

  return (
    <section className="replacement-panel">
      <div className="replacement-panel-header">
        <div>
          <p className="eyebrow">Phase 4</p>
          <h2>Apply Replacement</h2>
        </div>
        <span className="phase-badge">Regex Ready</span>
      </div>

      <form className="replacement-form" onSubmit={handleSubmit}>
        <label className="field-block" htmlFor="replacement-value">
          <span>Replacement value</span>
          <input
            id="replacement-value"
            className="replacement-input"
            type="text"
            placeholder="REDACTED"
            value={replacementValue}
            disabled={isLoading}
            onChange={(event) => onReplacementChange(event.target.value)}
          />
        </label>

        <button className="replacement-button" type="submit" disabled={isLoading}>
          {isLoading ? "Applying" : "Apply Replacement"}
        </button>
      </form>
    </section>
  );
}
