import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // Proxy ALL /api requests to the Haystack server
      // The target should be the base URL without the path
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        secure: false,
        // Don't rewrite - preserve the full path including project name
        // e.g., /api/demo/about -> http://localhost:8080/api/demo/about
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'markdown': ['react-markdown'],
          'haystack': ['haystack-core', 'haystack-units', 'haystack-react'],
        },
      },
    },
  },
});
