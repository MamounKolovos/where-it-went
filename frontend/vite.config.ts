import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@components': path.resolve(__dirname, './src/components'),
      '@services': path.resolve(__dirname, './src/services'),
      '@app-types': path.resolve(__dirname, './src/types'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/socket.io': {
        target: 'http://10.133.199.209:5000', 
        ws: true,
      },
      '/api': 'http://10.133.199.209:5000',
      '/search-spending-by-award': 'http://10.133.199.209:5000',
      '/health': 'http://10.133.199.209:5000',
    },
  },
});

