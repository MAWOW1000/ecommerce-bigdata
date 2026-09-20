import path from "node:path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  // Build thang vao thu muc static cua FastAPI
  build: { outDir: "../src/ecommerce_bigdata/web/static/app", emptyOutDir: true },
  base: "/app/",
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000", "/static": "http://127.0.0.1:8000" },
  },
})
