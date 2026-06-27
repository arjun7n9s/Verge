import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The console talks to the FastAPI gateway on :8000. In dev we proxy /api and
// /health so the app can use same-origin paths.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
