/**
 * Centralized API Helper for Nivesh Frontend
 * Reads NEXT_PUBLIC_API_URL from environment with fallback to http://localhost:8000
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
