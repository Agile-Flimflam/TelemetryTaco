import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        // docker compose points this at the backend service.
        target: process.env.API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/test/**',
        'src/shared/api/generated.ts',
        'src/vite-env.d.ts',
      ],
    },
  },
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          // A group also pulls in its dependencies, and the first group to reach a module
          // keeps it. Recharts depends on clsx, so if recharts-vendor came before ui-vendor,
          // clsx would land in the Recharts chunk and the entry would preload all of Recharts.
          groups: [
            {
              name: 'react-vendor',
              test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/,
            },
            {
              name: 'query-vendor',
              test: /[\\/]node_modules[\\/]@tanstack[\\/](react-query|query-core)[\\/]/,
            },
            {
              name: 'ui-vendor',
              test: /[\\/]node_modules[\\/](class-variance-authority|clsx|tailwind-merge|lucide-react)[\\/]/,
            },
            { name: 'recharts-vendor', test: /[\\/]node_modules[\\/]recharts[\\/]/ },
          ],
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
})
