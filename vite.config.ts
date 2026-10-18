import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// The app always calls same-origin /api. This proxy exists ONLY for `npm run dev` / `vite preview`
// and is never part of the production bundle: Vercel routes /api/* to the Python function.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')
  const target = env.DEV_API_PROXY || 'http://127.0.0.1:8000'
  return {
    plugins: [react()],
    server: { proxy: { '/api': target } },
    preview: { proxy: { '/api': target } },
    build: { chunkSizeWarningLimit: 700 },
  }
})
