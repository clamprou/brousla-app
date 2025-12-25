import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => {
  const isDev = mode === 'development'

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    build: {
      outDir: 'dist',
      // Source maps are useful in dev, but leak implementation details in production builds.
      sourcemap: isDev,
    },
    server: {
      port: 5173,
      strictPort: false,
    },
    css: {
      devSourcemap: isDev,
    },
    esbuild: {
      sourcemap: isDev,
    },
    optimizeDeps: {
      esbuildOptions: {
        sourcemap: isDev,
      },
    },
  }
})


