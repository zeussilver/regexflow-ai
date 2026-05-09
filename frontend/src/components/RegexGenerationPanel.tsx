import ColumnSelector from "./ColumnSelector";

interface RegexGenerationPanelProps {
  columns: string[];
  hasUploadedFile: boolean;
  isGenerating: boolean;
  naturalLanguage: string;
  targetColumn: string;
  onGenerate: () => void;
  onNaturalLanguageChange: (value: string) => void;
  onTargetColumnChange: (value: string) => void;
}

export default function RegexGenerationPanel({
  columns,
  hasUploadedFile,
  isGenerating,
  naturalLanguage,
  targetColumn,
  onGenerate,
  onNaturalLanguageChange,
  onTargetColumnChange,
}: RegexGenerationPanelProps) {
  const generateState = isGenerating ? "loading" : hasUploadedFile ? "ready" : "locked";

  return (
    <section className="regex-panel">
      <div className="regex-panel-header">
        <div>
          <h2>Generate Regex</h2>
        </div>
      </div>

      <div className="regex-form">
        <ColumnSelector
          columns={columns}
          value={targetColumn}
          disabled={!hasUploadedFile || isGenerating}
          onChange={onTargetColumnChange}
        />

        <label className="field-block" htmlFor="natural-language">
          <span>Pattern description</span>
          <textarea
            id="natural-language"
            placeholder="Find email addresses"
            value={naturalLanguage}
            disabled={!hasUploadedFile || isGenerating}
            onChange={(event) => onNaturalLanguageChange(event.target.value)}
          />
        </label>

        <button
          className="generate-button action-button"
          type="button"
          data-action-state={generateState}
          disabled={!hasUploadedFile || isGenerating}
          onClick={onGenerate}
        >
          {isGenerating ? "Generating" : "Generate Regex"}
        </button>
      </div>
    </section>
  );
}
