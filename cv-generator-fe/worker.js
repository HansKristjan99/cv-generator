// Cloudflare Worker entry point.
// Handles two concerns:
//   1. /api/* requests are proxied to the backend ALB (BACKEND_URL env var).
//   2. Everything else is served from the static Vite build; any path that
//      doesn't match a real asset falls back to index.html for React Router.

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname.startsWith("/api/")) {
      const backendUrl = (env.BACKEND_URL ?? "").replace(/\/$/, "");
      const backendPath = url.pathname.replace(/^\/api/, "");
      return fetch(new Request(backendUrl + backendPath + url.search, request));
    }

    const response = await env.ASSETS.fetch(request);
    if (response.status === 404) {
      const indexUrl = new URL(request.url);
      indexUrl.pathname = "/index.html";
      return env.ASSETS.fetch(new Request(indexUrl.href));
    }
    return response;
  },
};
