/// <reference types="vitest" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// En dev el SPA corre en :5174 y proxya /api al BFF en :8090 (un solo origen
// también en dev; el servicio media-plane NO tiene CORS y nunca se toca directo).
//
// 5174 y no el 5173 por defecto de Vite: en la máquina de desarrollo los puertos
// 3000 y 5173 están tomados por otro proyecto. `strictPort` hace que el arranque
// falle en vez de saltar a otro puerto en silencio, que es peor: el proxy sigue
// funcionando pero la pestaña abierta apunta al servidor viejo.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://localhost:8090', ws: true },
    },
  },
  test: {
    environment: 'jsdom',
  },
})
