import react from "@vitejs/plugin-react";
import { execSync } from "child_process";
import { resolve } from "path";
import { defineConfig } from "vite";

// Prefer API on :8000; fall back to :8001 (common local alternate).
// If neither is listening, disable the proxy so Vite does not spam ECONNREFUSED.
function detectApiTarget(): string | null {
  try {
    const cmd = process.platform === "win32" ? "netstat -ano" : "netstat -an";
    const output = execSync(cmd, { encoding: "utf8" });
    if (/:8000\b/.test(output)) return "http://localhost:8000";
    if (/:8001\b/.test(output)) return "http://localhost:8001";
  } catch {
    return "http://localhost:8000";
  }
  return null;
}

const apiTarget = detectApiTarget();

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
  server: {
    // 5173 is often taken by other local Vite apps; try 5174 next.
    port: 5174,
    strictPort: false,
    host: "127.0.0.1",
    proxy: apiTarget
      ? {
          "/api": {
            target: apiTarget,
            changeOrigin: true,
          },
          "/health": {
            target: apiTarget,
            changeOrigin: true,
          },
        }
      : {},
  },
});
