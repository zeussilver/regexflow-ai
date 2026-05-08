import axios from "axios";

import {
  PhoneNormalizationRequest,
  PhoneNormalizationResponse,
  PiiRedactionRequest,
  PiiRedactionResponse,
  TransformationApiError,
  TransformationApiErrorPayload,
} from "../types/transformations";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api",
});

export async function redactPii(payload: PiiRedactionRequest): Promise<PiiRedactionResponse> {
  try {
    const response = await apiClient.post<PiiRedactionResponse>(
      "/transformations/pii-redact/",
      payload,
    );
    return response.data;
  } catch (error) {
    throw toTransformationApiError(
      error,
      "PII_REDACTION_FAILED",
      "PII redaction could not be applied. Check that Django is running and try again.",
    );
  }
}

export async function normalizePhones(
  payload: PhoneNormalizationRequest,
): Promise<PhoneNormalizationResponse> {
  try {
    const response = await apiClient.post<PhoneNormalizationResponse>(
      "/transformations/phone-normalize/",
      payload,
    );
    return response.data;
  } catch (error) {
    throw toTransformationApiError(
      error,
      "PHONE_NORMALIZATION_FAILED",
      "Phone normalization could not be applied. Check that Django is running and the LLM is configured.",
    );
  }
}

function toTransformationApiError(
  error: unknown,
  fallbackCode: string,
  fallbackMessage: string,
): TransformationApiError {
  if (axios.isAxiosError<TransformationApiErrorPayload>(error)) {
    const payload = error.response?.data;
    if (payload?.error) {
      return new TransformationApiError(payload.error.code, payload.error.message);
    }
  }

  return new TransformationApiError(fallbackCode, fallbackMessage);
}
