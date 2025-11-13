import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  // Usar la raíz del proyecto para desarrollo; `public/` se usa como publicDir.
  root: '.',
  publicDir: 'public',
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        // Usar process.cwd() en lugar de __dirname para mayor compatibilidad
        main: resolve(process.cwd(), 'index.html'),
      },
    },
  },
  server: {
    port: 3000,
    open: true,
  },
  resolve: {
    alias: {
  '@': resolve(process.cwd(), 'src'),
  '@styles': resolve(process.cwd(), 'src', 'styles'),
    },
  },
  
});
