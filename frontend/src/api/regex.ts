import axios from "axios";

import { apiClient } from "./client";
import {
  RegexApiError,
  RegexApiErrorPayload,
  RegexGenerateRequest,
  RegexGenerateResponse,
  RegexReplaceRequest,
  RegexReplaceResponse,
} from "../types/regex";

export async function generateRegex(
  payload: RegexGenerateRequest,
): Promise<RegexGenerateResponse> {
  try {
    const response = await apiClient.post<RegexGenerateResponse>("/regex/generate/", payload);
    return response.data;
  } catch (error) {
    throw toRegexApiError(
      error,
      "REGEX_GENERATION_FAILED",
      "The regex could not be generated. The backend API is unavailable; check the configured API URL and try again.",
    );
  }
}

export async function applyReplacement(
  payload: RegexReplaceRequest,
): Promise<RegexReplaceResponse> {
  try {
    const response = await apiClient.post<RegexReplaceResponse>("/regex/replace/", payload);
    return response.data;
  } catch (error) {
    throw toRegexApiError(
      error,
      "REGEX_REPLACEMENT_FAILED",
      "The replacement could not be applied. The backend API is unavailable; check the configured API URL and try again.",
    );
  }
}

function toRegexApiError(
  error: unknown,
  fallbackCode: string,
  fallbackMessage: string,
): RegexApiError {
  if (axios.isAxiosError<RegexApiErrorPayload>(error)) {
    const payload = error.response?.data;
    if (payload?.error) {
      return new RegexApiError(payload.error.code, payload.error.message);
    }
  }

  return new RegexApiError(fallbackCode, fallbackMessage);
}
