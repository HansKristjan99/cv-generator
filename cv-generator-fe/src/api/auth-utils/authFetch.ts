type TokenProvider = () => Promise<string | null>;

let tokenProvider: TokenProvider | null = null;

export function setAuthTokenProvider(provider: TokenProvider | null) {
  tokenProvider = provider;
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

  return fetch(input, { ...init, headers });
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
