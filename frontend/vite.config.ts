/// <reference types="vitest" />
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // Vitest's default include picks up tests/e2e/*.spec.ts too — but
    // those are Playwright specs that depend on @playwright/test (not
    // jsdom) and would crash here. Pin the include glob to src/.
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
});
