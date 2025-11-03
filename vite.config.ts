import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  },
  server: {
    sourcemapIgnoreList: false,
    port: 5173,
    strictPort: false
  },
  // Enable source maps in development for debugging
  css: {
    devSourcemap: true
  },
  // Ensure source maps are enabled for debugging
  esbuild: {
    sourcemap: true
  },
  optimizeDeps: {
    esbuildOptions: {
      sourcemap: true
    }
  }
})


