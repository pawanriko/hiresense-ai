# HireSense AI — React frontend

The single-page app for HireSense AI: Login, Dashboard, Resumes
(upload + ATS detail), JD Match (draft/edit criteria, run, analysis),
Mock Interview (start, answer, report), Applications and Gap Tasks.

It talks to the Django JSON API in `../api/` using **InsForge JWT
auth**: the browser signs in against InsForge (email + password, or
Google via InsForge) and sends the access token as an
`Authorization: Bearer` header on every call — see `src/insforge.js`
and `../api/insforge_auth.py`. No CORS: in development, Vite proxies
`/api` to Django on :8000; in production, Django serves the built app
itself (same origin). Two build-time env vars are required —
`VITE_INSFORGE_URL` and `VITE_INSFORGE_ANON_KEY`, in a `frontend/.env`
file (gitignored) or the deploy environment.

## Develop

Run Django first (repo root: `python manage.py runserver`), then:

```bash
npm install
npm run dev        # http://localhost:5173, hot reload, /api proxied
```

## Build

```bash
npm run build      # outputs dist/ — Django serves it under /static/
```

`vite.config.js` sets the production base to `/static/`; dev stays `/`.

## Notes

- **Styling** is one plain CSS file, `src/index.css` — a monochrome
  editorial design system. Every colour is a CSS variable; the header
  toggle sets `data-theme="light"` on `<html>` to invert the palette,
  persists to `localStorage`, and `index.html` applies it before first
  paint. Pages share the classes `.card`, `.row`, `.score`, `.muted`,
  `.pass`/`.fail`, `.list`, `.narrow` — restyle there, not per page.
- **CSRF:** not used — Bearer-verified API calls are exempt on the
  server (a token is not a cookie). The HTML pages still use
  Django sessions + CSRF tokens as before.
- Routes mirror the Django pages they replaced; `../config/urls.py`
  lists them as `SPA_ROUTES` so production serves the app shell for
  each one.
