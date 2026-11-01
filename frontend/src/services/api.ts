import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { notify } from "@/composables/useNotify";

const baseURL = process.env.VUE_APP_API_URL || "http://localhost:5000/api";
const api = axios.create({ baseURL, withCredentials: true, headers: { "Content-Type": "application/json" }, timeout: 30000 });
let refreshPromise: Promise<void> | null = null;

function readCookie(name: string): string | null {
  const match = document.cookie.split("; ").find((part) => part.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.substring(name.length + 1)) : null;
}

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean };
api.interceptors.request.use((config) => {
  const method = (config.method || "get").toLowerCase();
  config.timeout = (config.url || "").includes("/v1/chat/") ? 180000 : 30000;
  if (!["get", "head", "options"].includes(method)) {
    const isRefresh = (config.url || "").includes("/auth/refresh");
    const csrf = readCookie(isRefresh ? "csrf_refresh_token" : "csrf_access_token");
    if (csrf) config.headers.set("X-CSRF-TOKEN", csrf);
  }
  return config;
});

api.interceptors.response.use((response) => response, async (error: AxiosError) => {
  const original = error.config as RetryConfig | undefined;
  const url = original?.url || "";
  const excluded = ["/auth/login", "/auth/register", "/auth/refresh", "/auth/logout"];
  const canRefresh = error.response?.status === 401 && original && !original._retry && !excluded.some((path) => url.includes(path));
  if (canRefresh) {
    original._retry = true;
    refreshPromise ??= api.post("/auth/refresh", {}).then(() => undefined).finally(() => { refreshPromise = null; });
    try { await refreshPromise; return api.request(original); }
    catch (refreshError) { return Promise.reject(refreshError); }
  }
  const detail = (error.response?.data as any)?.detail || (error.response?.data as any)?.message;
  const message = typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : error.message || "Something went wrong. Please try again.";
  notify(message, "error");
  return Promise.reject(error);
});

export function apiErrorMessage(error: unknown): string {
  const axiosError = error as AxiosError<{ detail?: string; message?: string }>;
  const detail = axiosError.response?.data?.detail || axiosError.response?.data?.message;
  return (typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : "") || axiosError.message || "Something went wrong. Please try again.";
}

export default api;
