import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load environment variables
  const env = loadEnv(mode, process.cwd(), '')

  // Determine target URLs based on environment
  const backendUrl = env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
  const bffUrl = env.VITE_BFF_BASE_URL || 'http://127.0.0.1:8001'

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        // BFF API routes (new)
        '/api/v1': {
          target: bffUrl,
          changeOrigin: true,
          ws: true,
          configure: (proxy) => {
            proxy.on('error', (err) => {
              console.log('BFF proxy error:', err)
            })
            proxy.on('proxyReq', (_proxyReq, req) => {
              console.log('BFF proxy request:', req.method, req.url)
            })
          }
        },

        // Backend routes (existing - maintained for rollback)
        '/backtests': {
          target: backendUrl,
          changeOrigin: true,
          ws: true,
        },
        '/healthz': {
          target: backendUrl,
          changeOrigin: true,
        },
        '/bars': {
          target: backendUrl,
          changeOrigin: true,
        }
      },
    },
  }
})
