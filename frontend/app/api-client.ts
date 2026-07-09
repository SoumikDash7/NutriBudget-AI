import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to attach JWT token
apiClient.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

/**
 * Helper: extract a human-readable error message from an API error.
 * Backend may return { detail: "..." } (FastAPI default) or
 * { message: "..." } (our custom error_response wrapper).
 */
export function getApiError(err: any): string {
  // No response object = network-level failure (server offline / CORS preflight killed)
  if (!err?.response) {
    const code: string = err?.code ?? "";
    if (
      code === "ERR_NETWORK" ||
      code === "ERR_CONNECTION_REFUSED" ||
      code === "ECONNREFUSED"
    ) {
      return "Cannot reach the server. Please make sure the backend is running.";
    }
    return "Network error. Please check your connection and try again.";
  }
  return (
    err.response.data?.detail ||
    err.response.data?.message ||
    `Unexpected error (${err.response.status}). Please try again.`
  );
}

// Auth endpoint prefixes that should NEVER trigger the token-refresh interceptor.
// Intercepting a 401 from /auth/login and trying to refresh would cause a redirect loop.
const AUTH_ENDPOINTS = ["/auth/login", "/auth/register", "/auth/refresh", "/auth/send-otp", "/auth/verify-otp", "/auth/forgot-password", "/auth/reset-password"];

// Response interceptor to handle token expiration
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const isAuthEndpoint = AUTH_ENDPOINTS.some((path) =>
      originalRequest?.url?.includes(path)
    );

    // Only attempt refresh for non-auth endpoints with 401 errors
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !isAuthEndpoint
    ) {
      originalRequest._retry = true;
      try {
        const refreshToken = localStorage.getItem("refresh_token");
        if (refreshToken) {
          const res = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const { access_token, refresh_token } = res.data;
          localStorage.setItem("access_token", access_token);
          localStorage.setItem("refresh_token", refresh_token);
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        if (typeof window !== "undefined") {
          window.location.href = "/";
        }
      }
    }
    return Promise.reject(error);
  }
);
