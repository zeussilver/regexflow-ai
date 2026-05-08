import { useState } from "react";

import { uploadFile } from "../api/files";
import DataPreviewTable from "../components/DataPreviewTable";
import ErrorMessage from "../components/ErrorMessage";
import FileUploader from "../components/FileUploader";
import { FileUploadResponse, UploadApiError } from "../types/files";

export default function HomePage() {
  const [previewData, setPreviewData] = useState<FileUploadResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  async function handleUpload(file: File) {
    setIsUploading(true);
    setErrorMessage(null);

    try {
      const response = await uploadFile(file);
      setPreviewData(response);
    } catch (error) {
      setPreviewData(null);
      setErrorMessage(errorToMessage(error));
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <main className="app-shell">
      <FileUploader
        isUploading={isUploading}
        onUpload={handleUpload}
        onClientError={(message) => setErrorMessage(message || null)}
      />
      <ErrorMessage message={errorMessage} />
      <DataPreviewTable data={previewData} />
    </main>
  );
}

function errorToMessage(error: unknown): string {
  if (error instanceof UploadApiError) {
    return error.message;
  }

  return "The upload failed. Check the file and try again.";
}
