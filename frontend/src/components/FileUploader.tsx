import { ChangeEvent, FormEvent, useState } from "react";

interface FileUploaderProps {
  isUploading: boolean;
  onUpload: (file: File) => Promise<void>;
  onClientError: (message: string) => void;
}

export default function FileUploader({
  isUploading,
  onUpload,
  onClientError,
}: FileUploaderProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    setSelectedFile(nextFile);
    onClientError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedFile) {
      onClientError("Choose a CSV or XLSX file before uploading.");
      return;
    }

    await onUpload(selectedFile);
  }

  return (
    <form className="upload-panel" onSubmit={handleSubmit}>
      <div className="upload-copy">
        <h1>RegexFlow AI</h1>
      </div>

      <div className="upload-controls">
        <label className="file-input-label" htmlFor="file-upload">
          <span className="file-input-title">
            {selectedFile ? selectedFile.name : "Select CSV or XLSX"}
          </span>
          <span className="file-input-meta">
            {selectedFile ? `${formatBytes(selectedFile.size)}` : "Max 5 MB"}
          </span>
        </label>
        <input
          id="file-upload"
          type="file"
          accept=".csv,.xlsx"
          onChange={handleFileChange}
          disabled={isUploading}
        />
        <button type="submit" disabled={isUploading}>
          {isUploading ? "Uploading" : "Upload"}
        </button>
      </div>
    </form>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  const kilobytes = bytes / 1024;
  if (kilobytes < 1024) {
    return `${kilobytes.toFixed(1)} KB`;
  }

  return `${(kilobytes / 1024).toFixed(1)} MB`;
}
