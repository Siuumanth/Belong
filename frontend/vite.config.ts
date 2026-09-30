import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // All traffic goes through the Go gateway on :9000.
      // Gateway validates JWT, injects X-User-ID, then forwards:
      //   /auth/*       → auth service :9001  (gateway strips /auth prefix)
      //   /profiles/*   → python :8000
      //   /onboarding/* → python :8000
      //   /matches/*    → python :8000
      // Python now serves all routes without the /api prefix.
      "/auth": {
        target: "http://localhost:9000",
        changeOrigin: true,
      },
      "/profiles": {
        target: "http://localhost:9000",
        changeOrigin: true,
      },
      "/onboarding": {
        target: "http://localhost:9000",
        changeOrigin: true,
      },
      "/matches": {
        target: "http://localhost:9000",
        changeOrigin: true,
      },
      "/health": {
        target: "http://localhost:9000",
        changeOrigin: true,
      },
    },
  },
});
