import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // React core (used by almost every page, cached separately)
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          // ReactFlow + d3 dependencies (only used by JobsPanel, lazy loaded)
          'vendor-reactflow': ['reactflow'],
          // Markdown rendering (used by multiple panels, but not required for initial load)
          'vendor-markdown': ['react-markdown', 'remark-gfm', 'rehype-raw'],
          // Radix UI component library
          'vendor-radix': [
            '@radix-ui/react-popover',
            '@radix-ui/react-scroll-area',
            '@radix-ui/react-tabs',
            '@radix-ui/react-tooltip',
          ],
        },
      },
    },
  },
  server: {
    port: 5173,
    // SSH port forwarding scenario: disable HMR WebSocket to avoid connection drops causing forwarding failures
    hmr: false,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
