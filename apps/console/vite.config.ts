import react from "@vitejs/plugin-react";
import { execSync } from "child_process";
import { resolve } from "path";
import { defineConfig } from "vite";

// Detect if the FastAPI gateway is actively running on port 8000.
// If it is offline, we disable the proxy configuration completely to prevent Vite
// from spamming ECONNREFUSED connection traces to the terminal.
let isBackendUp = false;
try {
  const cmd = process.platform === "win32" ? "netstat -ano" : "netstat -an";
  const output = execSync(cmd, { encoding: "utf8" });
  isBackendUp = /:8000\b/.test(output);
} catch {
  // If detection fails, assume backend is up so proxying still works cross-platform
  isBackendUp = true;
}

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5173,
    proxy: isBackendUp
      ? {
          "/api": {
            target: "http://localhost:8000",
            changeOrigin: true,
          },
          "/health": {
            target: "http://localhost:8000",
            changeOrigin: true,
          },
        }
      : {},
  },
});
