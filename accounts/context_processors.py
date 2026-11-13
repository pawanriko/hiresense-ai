"""Template context processors for the accounts app.

Empty since the InsForge swap (Phase 5): the only processor that ever
lived here exposed ``google_oauth_configured`` for the django-allauth
Google button on the login page. Allauth is gone, Google sign-in now
lives in InsForge, and no template needs the flag. The module remains
so the app's import surface stays stable.
"""
