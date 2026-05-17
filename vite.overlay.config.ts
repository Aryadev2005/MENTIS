import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  root: "renderer",
  base: "./",
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "renderer/src"),
    },
  },
  build: {
    outDir: "../dist/overlay",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        overlay: path.resolve(__dirname, "renderer/overlay.html"),
      },
    },
  },
  server: {
    port: 5174,
    strictPort: true,
  },
});
