/**
 * Centralized API Helper for Nivesh Frontend
 *
 * - In production (Vercel): When running in any browser outside localhost/127.0.0.1,
 *   API_BASE automatically resolves to "" (relative URL), sending fetches to /api/...
 *   which Next.js and Vercel route to the Python serverless function.
 *
 * - In development: Next.js dev server rewrites /api/* -> http://127.0.0.1:8000/api/*
 */

function getApiBase(): string {
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    // If running in browser on a production domain (not local dev), force relative URLs
    if (hostname !== "localhost" && hostname !== "127.0.0.1" && hostname !== "0.0.0.0") {
      return "";
    }
  }

  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl.startsWith("http")) {
    return envUrl;
  }
  return "";
}

const API_BASE = getApiBase();

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
