# HireSense AI — React frontend

The single-page app for HireSense AI: Login, Dashboard, Resumes
(upload + ATS detail), JD Match (draft/edit criteria, run, analysis),
Mock Interview (start, answer, report), Applications and Gap Tasks.

It talks to the Django JSON API in `../api/` using **Django session
auth**: email + password through `/api/auth/` (session cookie +
`X-CSRFToken` header), or Google/GitHub through django-allauth under
`/accounts/` — see `src/api.js` and `../api/auth_views.py`. No CORS:
in development, Vite proxies `/api` to Django on :8000; in
production, Django serves the built app itself (same origin). No
frontend env vars are needed for auth; OAuth credentials live on the
backend (`GOOGLE_OAUTH_*` / `GITHUB_OAUTH_*`).

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
