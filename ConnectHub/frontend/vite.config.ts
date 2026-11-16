import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies API + WebSocket traffic to the FastAPI process so the
// browser can use same-origin relative URLs (no CORS or mixed-content issues).
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: "ws://127.0.0.1:8000",
        ws: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
