import axios from "axios";

const localApiBaseUrl = "http://localhost:8000/api";

function resolveApiBaseUrl(): string {
  const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
  return configuredApiBaseUrl || localApiBaseUrl;
}

export const apiBaseUrl = resolveApiBaseUrl().replace(/\/+$/, "");

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
});
