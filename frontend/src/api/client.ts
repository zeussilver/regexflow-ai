import axios from "axios";

const defaultApiBaseUrl = import.meta.env.DEV
  ? "http://localhost:8000/api"
  : "https://regexflow-ai-backend.onrender.com/api";

function resolveApiBaseUrl(): string {
  const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
  return configuredApiBaseUrl || defaultApiBaseUrl;
}

export const apiBaseUrl = resolveApiBaseUrl().replace(/\/+$/, "");

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
});
