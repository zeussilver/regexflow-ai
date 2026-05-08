import axios from "axios";

import { apiBaseUrl, apiClient } from "./client";
import { ApiErrorPayload, FileUploadResponse, UploadApiError } from "../types/files";

export async function uploadFile(file: File): Promise<FileUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await apiClient.post<FileUploadResponse>("/files/upload/", formData);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError<ApiErrorPayload>(error)) {
      const payload = error.response?.data;
      if (payload?.error) {
        throw new UploadApiError(payload.error.code, payload.error.message);
      }
    }

    throw new UploadApiError(
      "UPLOAD_FAILED",
      "The file could not be uploaded. The backend API is unavailable; check the configured API URL and try again.",
    );
  }
}

export function getProcessedFileDownloadUrl(processedFileId: string): string {
  return `${apiBaseUrl}/files/processed/${encodeURIComponent(processedFileId)}/download/`;
}
