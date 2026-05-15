import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const flaskTarget = process.env.VITE_FLASK_ORIGIN ?? 'http://127.0.0.1:3000'

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: 'dist',
    assetsDir: 'dist-assets',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/ocr': flaskTarget,
      '/identify': flaskTarget,
      '/summarize': flaskTarget,
      '/assets': flaskTarget,
    },
  },
})
