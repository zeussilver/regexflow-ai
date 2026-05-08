interface ColumnSelectorProps {
  columns: string[];
  value: string;
  disabled: boolean;
  onChange: (column: string) => void;
}

export default function ColumnSelector({
  columns,
  value,
  disabled,
  onChange,
}: ColumnSelectorProps) {
  return (
    <label className="field-block" htmlFor="target-column">
      <span>Target column</span>
      <select
        id="target-column"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">Choose a column</option>
        {columns.map((column) => (
          <option key={column} value={column}>
            {column}
          </option>
        ))}
      </select>
    </label>
  );
}
