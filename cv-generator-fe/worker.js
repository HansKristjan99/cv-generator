// Cloudflare Worker — serves the static Vite build.
// API calls go directly from the browser to the backend (VITE_API_BASE_URL,
// embedded at build time).  CORS is handled by the FastAPI backend.

const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "script-src 'self' https://js.stripe.com https://*.js.stripe.com https://checkout.stripe.com https://*.clerk.com https://*.clerk.accounts.dev https://clerk.vericodehq.com",
  "script-src-elem 'self' https://js.stripe.com https://*.js.stripe.com https://checkout.stripe.com https://*.clerk.com https://*.clerk.accounts.dev https://clerk.vericodehq.com",
  "worker-src 'self' blob:",
  "child-src 'self' blob: https://js.stripe.com https://*.js.stripe.com https://checkout.stripe.com https://m.stripe.network",
  "frame-src 'self' data: https://js.stripe.com https://*.js.stripe.com https://hooks.stripe.com https://checkout.stripe.com https://m.stripe.network https://*.clerk.com https://*.clerk.accounts.dev https://clerk.vericodehq.com",
  "connect-src 'self' https://api.vericodehq.com https://api.stripe.com https://checkout.stripe.com https://js.stripe.com https://m.stripe.network https://*.clerk.com https://*.clerk.accounts.dev https://clerk.vericodehq.com",
  "img-src 'self' data: blob: https://*.stripe.com https://*.clerk.com https://*.clerk.accounts.dev https://img.clerk.com",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com",
  "form-action 'self'",
].join("; ");

function withSecurityHeaders(response) {
  const next = new Response(response.body, response);
  next.headers.set("Content-Security-Policy", CONTENT_SECURITY_POLICY);
  return next;
}

export default {
  async fetch(request, env) {
    const response = await env.ASSETS.fetch(request);
    if (response.status === 404) {
      const indexUrl = new URL(request.url);
      indexUrl.pathname = "/index.html";
      return withSecurityHeaders(await env.ASSETS.fetch(new Request(indexUrl.href)));
    }
    return withSecurityHeaders(response);
  },
};
