import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Auth service: Go on :9001 — strip the /auth prefix
      "/auth": {
        target: "http://localhost:9001",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/auth/, ""),
      },
      // Python API: FastAPI on :8000 — strip the leading slash and let /api prefix through
      "/profiles": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => `/api${path}`,
      },
      "/onboarding": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => `/api${path}`,
      },
      "/matches": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => `/api${path}`,
      },
      "/embeddings": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => `/api${path}`,
      },
      "/health": {
        target: "http://localhost:9001",
        changeOrigin: true,
      },
    },
  },
});
