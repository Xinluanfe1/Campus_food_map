import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 本地开发时，前端把 /api 开头的请求代理到 FastAPI 后端，避免跨域配置问题。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
