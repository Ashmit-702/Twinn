import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Dev only: when VITE_API_URL is empty, /api is proxied to the local FastAPI server.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react()],
    server: { proxy: { '/api': env.DEV_API_PROXY || 'http://127.0.0.1:8000' } },
  }
})
