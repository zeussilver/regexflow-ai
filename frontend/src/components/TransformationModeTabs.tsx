import { TransformationMode } from "../types/transformations";

interface TransformationModeTabsProps {
  mode: TransformationMode;
  onModeChange: (mode: TransformationMode) => void;
}

const tabs: Array<{ mode: TransformationMode; label: string }> = [
  { mode: "pii_redaction", label: "PII Redaction Assistant" },
  { mode: "phone_normalization", label: "Phone Normalization" },
];

export default function TransformationModeTabs({
  mode,
  onModeChange,
}: TransformationModeTabsProps) {
  return (
    <section className="transformation-tabs-panel">
      <div className="transformation-tabs-header">
        <div>
          <h2>Transformations</h2>
        </div>
      </div>

      <div className="transformation-tabs" role="tablist" aria-label="Transformation modes">
        {tabs.map((tab) => (
          <button
            key={tab.mode}
            className={tab.mode === mode ? "transformation-tab active" : "transformation-tab"}
            type="button"
            role="tab"
            aria-selected={tab.mode === mode}
            onClick={() => onModeChange(tab.mode)}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </section>
  );
}
