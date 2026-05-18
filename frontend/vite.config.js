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
      '/api': {
        target: 'http://127.0.0.1:8000',  // explicit IPv4 — Node 18+ resolves 'localhost' as ::1 (IPv6) first
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      },
    },
  },
})
