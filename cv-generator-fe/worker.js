// Cloudflare Worker entry point.
// Handles two concerns:
//   1. /api/* requests are proxied to the backend ALB (BACKEND_URL env var).
//   2. Everything else is served from the static Vite build; any path that
//      doesn't match a real asset falls back to index.html for React Router.

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname.startsWith("/api/")) {
      let backendUrl = (env.BACKEND_URL ?? "").replace(/\/$/, "");
      if (backendUrl && !backendUrl.startsWith("http")) {
        backendUrl = "http://" + backendUrl;
      }
      const backendPath = url.pathname.replace(/^\/api/, "");
      const targetUrl = backendUrl + backendPath + url.search;

      const headers = new Headers();
      for (const [key, value] of request.headers) {
        if (!key.startsWith("cf-") && key !== "host") {
          headers.set(key, value);
        }
      }

      return fetch(targetUrl, {
        method: request.method,
        headers,
        body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
      });
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
