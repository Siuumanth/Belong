import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Auth goes to gateway → gateway strips /auth and forwards to auth service :9001
      "/auth": {
        target: "http://localhost:9000",
        changeOrigin: true,
      },
      // All domain API calls go through the gateway under /api
      // Gateway mounts /api → strips prefix → forwards to Python :8000 with /api prefix intact
      "/api": {
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
