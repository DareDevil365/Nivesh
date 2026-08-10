/**
 * Centralized API Helper for Nivesh Frontend
 *
 * - In production (Vercel): NEXT_PUBLIC_API_URL is unset → API_BASE = ""
 *   All fetch("/api/...") calls are relative, handled by the Vercel Python serverless function.
 *
 * - In development: next.config.mjs rewrites /api/* → http://127.0.0.1:8000/api/*
 *   so NEXT_PUBLIC_API_URL does NOT need to be set locally either.
 *
 * - Override: Set NEXT_PUBLIC_API_URL to an absolute URL only if you need to point
 *   to a remote backend explicitly (e.g., a staging backend).
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorText = await response.text().catch(() => "Unknown error");
    throw new Error(`API Error [${response.status}]: ${errorText}`);
  }
  return response.json();
}

export const api = {
  get: async <T = any>(path: string): Promise<T> => {
    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    const response = await fetch(`${API_BASE}${cleanPath}`);
    return handleResponse<T>(response);
  },

  post: async <T = any>(path: string, body?: any): Promise<T> => {
    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    const response = await fetch(`${API_BASE}${cleanPath}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
  },

  delete: async <T = any>(path: string): Promise<T> => {
    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    const response = await fetch(`${API_BASE}${cleanPath}`, {
      method: "DELETE",
    });
    return handleResponse<T>(response);
  },
};
