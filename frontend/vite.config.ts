import { defineConfig } from 'vite';

export default defineConfig({
  root: 'public',
  base: './',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
});
