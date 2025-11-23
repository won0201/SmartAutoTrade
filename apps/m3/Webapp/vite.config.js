// vite.config.js

import { defineConfig } from 'vite';


import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 2027,
    host: '0.0.0.0',
    open: true
  }
})

