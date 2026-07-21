import react from "@vitejs/plugin-react";
import { execSync } from "child_process";
import { resolve } from "path";
import { defineConfig } from "vite";

// Always proxy /api — never fall back to SPA HTML (that makes Initiate demo a no-op).
// Prefer :8000, then :8001; override with VERGE_API_PROXY.
function detectApiTarget(): string {
  const fromEnv = (process.env.VERGE_API_PROXY || "").trim();
  if (fromEnv) return fromEnv;
  try {
    const cmd = process.platform === "win32" ? "netstat -ano" : "netstat -an";
    const output = execSync(cmd, { encoding: "utf8" });
    if (/:8000\s/.test(output) || /:8000\b/.test(output)) {
      return "http://127.0.0.1:8000";
    }
    if (/:8001\s/.test(output) || /:8001\b/.test(output)) {
      return "http://127.0.0.1:8001";
    }
  } catch {
    /* keep default */
  }
  return "http://127.0.0.1:8001";
}

const apiTarget = detectApiTarget();
// eslint-disable-next-line no-console
console.log(`[vite] API proxy → ${apiTarget}`);

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  server: {
    // 5173 is often taken by other local Vite apps.
    port: 5174,
    strictPort: false,
    host: "127.0.0.1",
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
      "/health": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
});
