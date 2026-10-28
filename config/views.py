"""Project-level views: the React SPA shell and root-level site files.

These exist for production (Render), where Django itself serves the
built React app. In local dev the browser talks to Vite on :5173, so
these views are never hit — but they are harmless there too.
"""

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound


def _built_file(name):
    """Find a file from the built frontend, preferring the collected
    copy (STATIC_ROOT, what WhiteNoise serves) and falling back to the
    raw Vite output (frontend/dist). Returns a Path, or None."""
    for candidate in (settings.STATIC_ROOT / name,
                      settings.BASE_DIR / 'frontend' / 'dist' / name):
        if candidate.is_file():
            return candidate
    return None


def spa_index(request):
    """The React app's shell page, for every SPA route in config/urls.py.

    The HTML is tiny (it just boots /static/assets/*.js), so it is read
    into memory rather than streamed. When no build exists yet (fresh
    clone, `npm run build` not run), this is an honest 404 telling the
    developer what to run — not a blank page.
    """
    index = _built_file('index.html')
    if index is None:
        return HttpResponseNotFound(
            'Frontend build not found. Run `npm run build` in frontend/.'
        )
    return HttpResponse(index.read_bytes(), content_type='text/html')


def site_file(request, name):
    """A root-level file from the built frontend (favicon.svg, icons.svg).

    Browsers ask for /favicon.svg at the site root, but collectstatic
    puts it at /static/favicon.svg — so this view bridges that gap.
    Only the names wired in config/urls.py can reach this view.
    """
    found = _built_file(name)
    if found is None:
        return HttpResponseNotFound()
    content_type = ('image/svg+xml' if name.endswith('.svg')
                    else 'application/octet-stream')
    return HttpResponse(found.read_bytes(), content_type=content_type)
