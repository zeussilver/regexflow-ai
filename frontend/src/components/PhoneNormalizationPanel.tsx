import { FormEvent } from "react";

import { PhoneTargetFormat } from "../types/transformations";

interface PhoneNormalizationPanelProps {
  columns: string[];
  defaultRegion: string;
  hasUploadedFile: boolean;
  isLoading: boolean;
  naturalLanguage: string;
  targetColumn: string;
  targetFormat: PhoneTargetFormat;
  onDefaultRegionChange: (value: string) => void;
  onNaturalLanguageChange: (value: string) => void;
  onNormalize: () => void;
  onTargetColumnChange: (column: string) => void;
  onTargetFormatChange: (format: PhoneTargetFormat) => void;
}

const phoneFormats: PhoneTargetFormat[] = ["E164", "INTERNATIONAL", "NATIONAL", "RFC3966"];

export default function PhoneNormalizationPanel({
  columns,
  defaultRegion,
  hasUploadedFile,
  isLoading,
  naturalLanguage,
  targetColumn,
  targetFormat,
  onDefaultRegionChange,
  onNaturalLanguageChange,
  onNormalize,
  onTargetColumnChange,
  onTargetFormatChange,
}: PhoneNormalizationPanelProps) {
  const isDisabled = !hasUploadedFile || isLoading;
  const normalizeState = isLoading ? "loading" : hasUploadedFile ? "ready" : "locked";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onNormalize();
  }

  return (
    <section className="phone-panel" aria-label="Phone normalization">
      <div className="transformation-panel-header">
        <div>
          <p className="eyebrow">Phone Normalization</p>
          <h2>Normalize Phone Numbers</h2>
        </div>
      </div>

      <form className="transformation-form phone-form" onSubmit={handleSubmit}>
        <label className="field-block" htmlFor="phone-target-column">
          <span>Target column</span>
          <select
            id="phone-target-column"
            value={targetColumn}
            disabled={isDisabled}
            onChange={(event) => onTargetColumnChange(event.target.value)}
          >
            <option value="">Choose a column</option>
            {columns.map((column) => (
              <option key={column} value={column}>
                {column}
              </option>
            ))}
          </select>
        </label>

        <label className="field-block phone-instruction-field" htmlFor="phone-natural-language">
          <span>Instruction</span>
          <textarea
            id="phone-natural-language"
            value={naturalLanguage}
            disabled={isDisabled}
            onChange={(event) => onNaturalLanguageChange(event.target.value)}
          />
        </label>

        <label className="field-block" htmlFor="phone-default-region">
          <span>Default region</span>
          <input
            id="phone-default-region"
            className="field-input"
            type="text"
            value={defaultRegion}
            disabled={isDisabled}
            maxLength={2}
            onChange={(event) => onDefaultRegionChange(event.target.value.toUpperCase())}
          />
        </label>

        <label className="field-block" htmlFor="phone-target-format">
          <span>Target format</span>
          <select
            id="phone-target-format"
            value={targetFormat}
            disabled={isDisabled}
            onChange={(event) => onTargetFormatChange(event.target.value as PhoneTargetFormat)}
          >
            {phoneFormats.map((format) => (
              <option key={format} value={format}>
                {format}
              </option>
            ))}
          </select>
        </label>

        <button
          className="transformation-button phone-normalize-button action-button"
          type="submit"
          data-action-state={normalizeState}
          disabled={!hasUploadedFile || isLoading}
        >
          {isLoading ? "Normalizing" : "Normalize"}
        </button>
      </form>
    </section>
  );
}
