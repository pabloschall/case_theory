import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'

export default defineConfig(({ mode }) => {
  const rootEnv = loadEnv(mode, resolve(process.cwd(), '..'), '')
  const appName = process.env.APP_NAME || rootEnv.APP_NAME || 'Game Theory'

  return {
    define: { __APP_NAME__: JSON.stringify(appName) },
    plugins: [
      react(),
      {
        name: 'app-name-html',
        transformIndexHtml: (html: string) => html.split('%APP_NAME%').join(appName),
      },
    ],
    test: { environment: 'jsdom', setupFiles: './src/test-setup.ts' },
    server: {
      port: 5173,
      proxy: { '/api': { target: 'http://backend:8000', changeOrigin: true }, '/media': { target: 'http://backend:8000', changeOrigin: true }, '/health': { target: 'http://backend:8000' } },
    },
  }
})
