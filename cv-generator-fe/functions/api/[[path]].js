// Cloudflare Pages Function — proxies every /api/* request to the backend.
// Set BACKEND_URL in the Cloudflare Pages environment variables to the ALB DNS
// printed by `cdk deploy` (no trailing slash).
//
// /api/cv/generate/  →  <BACKEND_URL>/cv/generate/
export async function onRequest({ request, env }) {
  const url = new URL(request.url);
  const backendUrl = (env.BACKEND_URL ?? "").replace(/\/$/, "");
  const backendPath = url.pathname.replace(/^\/api/, "");

  return fetch(new Request(backendUrl + backendPath + url.search, request));
}
