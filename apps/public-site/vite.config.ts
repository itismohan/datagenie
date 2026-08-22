import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  base: process.env.VITE_BASE_PATH || "/",
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "./client/src") } },
  root: path.resolve(__dirname, "client"),
  build: { outDir: path.resolve(__dirname, "dist/public"), emptyOutDir: true },
});
