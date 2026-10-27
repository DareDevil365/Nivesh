const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
let workspaceReady: Promise<void> | null = null;
const pending = new Map<string, Promise<unknown>>();

async function responseData<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .map(
                (item: { loc?: string[]; msg?: string }) =>
                  `${item.loc?.slice(1).join(".") || "Input"}: ${item.msg}`,
              )
              .join("; ")
          : `Request failed (${response.status}). Please try again.`;
    throw new Error(message);
  }
  return response.json();
}

function initWorkspace() {
  if (!workspaceReady) {
    workspaceReady = fetch(`${API_BASE}/api/workspace`, {
      credentials: "include",
      signal: AbortSignal.timeout(15000),
    })
      .then(responseData)
      .then(() => undefined)
      .catch((error) => {
        workspaceReady = null;
        throw error;
      });
  }
  return workspaceReady;
}

async function request<T>(
  path: string,
  method: string,
  body?: unknown,
): Promise<T> {
  await initWorkspace();
  try {
    const response = await fetch(
      `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`,
      {
        method,
        credentials: "include",
        cache: "no-store",
        signal: AbortSignal.timeout(60000),
        ...(body !== undefined
          ? {
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(body),
            }
          : {}),
      },
    );
    return await responseData<T>(response);
  } catch (error) {
    if (
      error instanceof DOMException &&
      ["TimeoutError", "AbortError"].includes(error.name)
    ) {
      throw new Error(
        "The data provider took too long to respond. Please retry.",
      );
    }
    if (error instanceof TypeError)
      throw new Error(
        "Cannot reach the research service. Check your connection and retry.",
      );
    throw error;
  }
}

export const api = {
  get: <T = any>(path: string): Promise<T> => {
    const current = pending.get(path);
    if (current) return current as Promise<T>;
    const call = request<T>(path, "GET").finally(() => pending.delete(path));
    pending.set(path, call);
    return call;
  },
  post: <T = any>(path: string, body?: unknown) =>
    request<T>(path, "POST", body),
  delete: <T = any>(path: string) => request<T>(path, "DELETE"),
};
