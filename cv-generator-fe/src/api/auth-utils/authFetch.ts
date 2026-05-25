type TokenProvider = () => Promise<string | null>;

let tokenProvider: TokenProvider | null = null;

export function setAuthTokenProvider(provider: TokenProvider | null) {
  tokenProvider = provider;
}

// VITE_API_BASE_URL is required in every environment. It points at the FastAPI
// backend directly; there is no Vite or Cloudflare /api proxy.
const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

function resolveUrl(input: RequestInfo | URL): RequestInfo | URL {
  if (typeof input !== "string" || /^https?:\/\//.test(input)) return input;
  const path = input.startsWith("/") ? input : `/${input}`;
  if (!API_BASE) {
    throw new Error("VITE_API_BASE_URL is not configured");
  }
  return API_BASE.replace(/\/$/, "") + path;
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
