import axios from "axios";

import { apiClient } from "./client";
import {
  PhoneNormalizationRequest,
  PhoneNormalizationResponse,
  PiiRedactionRequest,
  PiiRedactionResponse,
  TransformationApiError,
  TransformationApiErrorPayload,
} from "../types/transformations";

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
      "PII redaction could not be applied. The backend API is unavailable; check the configured API URL and try again.",
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
      "Phone normalization could not be applied. The backend API is unavailable; check the configured API URL and try again.",
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
