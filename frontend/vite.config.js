import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // In dev, the FastAPI backend runs on :8000 — proxy /api so the browser sees one origin.
    proxy: { '/api': 'http://localhost:8000' },
  },
})
