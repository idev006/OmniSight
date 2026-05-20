import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import basicSsl from '@vitejs/plugin-basic-ssl'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue(), basicSsl()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    host: true,   // รับ connection จากมือถือใน network เดียวกัน (0.0.0.0)
    proxy: {
      // HTTP API + WebSocket upgrade ทั้งหมดผ่าน /api prefix
      // ws:true ทำให้ Vite proxy handle WebSocket upgrade ได้
      // wss (mobile) → Vite proxy → ws://127.0.0.1:8000 (backend plain HTTP)
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
      },
      // Health check — ใช้โดย AppLayout offline banner
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
