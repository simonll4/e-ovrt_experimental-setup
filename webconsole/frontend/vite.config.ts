/// <reference types="vitest" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// En dev el SPA corre en :5173 y proxya /api al BFF en :8090 (un solo origen
// también en dev; el servicio media-plane NO tiene CORS y nunca se toca directo).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://localhost:8090', ws: true },
    },
  },
  test: {
    environment: 'jsdom',
  },
})
