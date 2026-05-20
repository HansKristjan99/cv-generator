type TokenProvider = () => Promise<string | null>;

let tokenProvider: TokenProvider | null = null;

export function setAuthTokenProvider(provider: TokenProvider | null) {
  tokenProvider = provider;
}

// In production VITE_API_BASE_URL is the ALB URL (e.g. http://my-alb.amazonaws.com).
// In local dev it is empty and the Vite proxy handles /api/* instead.
const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

function resolveUrl(input: RequestInfo | URL): RequestInfo | URL {
  if (!API_BASE || typeof input !== "string") return input;
  return API_BASE.replace(/\/$/, "") + input.replace(/^\/api/, "");
}

export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  if (!tokenProvider) {
    throw new Error("Authentication is not ready");
  }

  const token = await tokenProvider();
  if (!token) {
    throw new Error("Unable to get an authentication token");
  }

  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);

  return fetch(resolveUrl(input), { ...init, headers });
}

export async function readErrorMessage(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
  } catch {
    // fall through
  }
  return `Request failed with status ${response.status}`;
}
