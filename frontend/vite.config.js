import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // BASE: in production Django serves the built files from /static/
  // (WhiteNoise + collectstatic), so built asset URLs must start with
  // /static/. In dev the base stays / so the Vite server works
  // unchanged at :5173. `mode` is 'production' for `vite build`.
  base: mode === 'production' ? '/static/' : '/',
  server: {
    // PROXY: during development the browser talks to Vite (:5173) and
    // Vite forwards every /api/* call to Django (:8000). The browser
    // therefore sees ONE origin, so Django's session + CSRF cookies
    // work with no CORS setup at all. In production the built files
    // are served by Django itself, so no proxy is needed there.
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
}))
