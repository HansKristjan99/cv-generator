// Cloudflare Worker — serves the static Vite build.
// API calls go directly from the browser to the backend (VITE_API_BASE_URL,
// embedded at build time).  CORS is handled by the FastAPI backend.

export default {
  async fetch(request, env) {
    const response = await env.ASSETS.fetch(request);
    if (response.status === 404) {
      const indexUrl = new URL(request.url);
      indexUrl.pathname = "/index.html";
      return env.ASSETS.fetch(new Request(indexUrl.href));
    }
    return response;
  },
};
