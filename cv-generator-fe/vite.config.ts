import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// The proxy target is set by API_BASE_URL in the active .env file.
// It is only used by the Vite dev server — not embedded in the browser bundle.
//
// npm run dev         → reads .env (or nothing)        → proxies to localhost:8000
// npm run dev:remote  → reads .env.remote              → proxies to your deployed ALB
//
// Create cv-generator-fe/.env.remote with:
//   API_BASE_URL=http://<your-alb-dns>.eu-north-1.elb.amazonaws.com

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  const apiTarget = env.API_BASE_URL || "http://localhost:8000";

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
  };
});
