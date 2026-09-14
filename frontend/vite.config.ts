import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/auth": { target: "http://localhost:9000", changeOrigin: true },
      "/profiles": { target: "http://localhost:9000", changeOrigin: true },
      "/onboarding": { target: "http://localhost:9000", changeOrigin: true },
      "/matches": { target: "http://localhost:9000", changeOrigin: true },
      "/health": { target: "http://localhost:9000", changeOrigin: true },
    },
  },
});
