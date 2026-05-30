import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiUrl = env.VITE_API_URL || 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/calls': apiUrl,
        '/bots': apiUrl,
        '/hubspot': apiUrl,
        '/health': apiUrl,
        '/webhook': apiUrl,
        '/settings': apiUrl,
        '/auth': apiUrl,
      },
    },
  }
})
