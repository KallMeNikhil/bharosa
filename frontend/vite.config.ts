/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const backend = process.env.BHAROSA_API_ORIGIN ?? "http://127.0.0.1:8000";

const polling = process.env.BHAROSA_WATCH_POLLING === "true";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    watch: polling ? { usePolling: true, interval: 300 } : undefined,
    proxy: {
      "/api": { target: backend, changeOrigin: true },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
  },
});
