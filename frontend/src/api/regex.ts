import axios from "axios";

import {
  RegexApiError,
  RegexApiErrorPayload,
  RegexGenerateRequest,
  RegexGenerateResponse,
  RegexReplaceRequest,
  RegexReplaceResponse,
} from "../types/regex";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api",
});

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
      "The regex could not be generated. Check that Django is running and the LLM is configured.",
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
      "The replacement could not be applied. Check that Django is running and try again.",
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
