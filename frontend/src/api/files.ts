import axios from "axios";

import { ApiErrorPayload, FileUploadResponse, UploadApiError } from "../types/files";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api",
});

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
      "The file could not be uploaded. Check that Django is running at http://localhost:8000 and reload the frontend.",
    );
  }
}
