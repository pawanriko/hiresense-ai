"""Tests for the env-driven DATABASES switch (SQLite <-> Supabase Postgres).

WHY THESE TESTS EXIST: the database backend is picked once, at import
time, from the DATABASE_URL environment variable — so a typo in the
parsing code would only show up when someone actually tries Postgres.
These tests pin the behaviour down without needing a live Postgres
server anywhere:

  * The parser itself is a pure function (config.settings
    ._database_from_url), so it is tested directly.
  * The "DATABASE_URL set -> Postgres, unset -> SQLite" wiring is tested
    by booting a real Django process in a subprocess with a controlled
    environment, because re-importing settings inside this test process
    would not re-run the module-level if/else.

SimpleTestCase is used throughout: no database access is needed, so the
tests never touch SQLite either.
"""

import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

from config.settings import _database_from_url

# BASE_DIR here is the project root (config/ lives one level below it).
BASE_DIR = Path(__file__).resolve().parent.parent

# A throwaway snippet that boots Django and prints the resolved engine.
# It runs in a subprocess so DATABASE_URL can be set/unset freely.
_PRINT_ENGINE = (
    "import os;"
    "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings');"
    "import django; django.setup();"
    "from django.conf import settings;"
    "print(settings.DATABASES['default']['ENGINE'])"
)


def _engine_with_env(database_url):
    """Boot Django in a subprocess and return its resolved DB engine."""
    env = dict(os.environ)
    # .env files must not leak into this check: settings loads .env from
    # the project root, but an explicit environment variable wins over
    # .env, and removing the key tests the unset path cleanly.
    env.pop('DATABASE_URL', None)
    if database_url is not None:
        env['DATABASE_URL'] = database_url
    result = subprocess.run(
        [sys.executable, '-c', _PRINT_ENGINE],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise AssertionError(
            f'Django failed to boot with DATABASE_URL={database_url!r}:\n'
            f'{result.stderr}'
        )
    return result.stdout.strip()


class DatabaseUrlParserTests(SimpleTestCase):
    def test_pooler_url(self):
        """Supabase's recommended form: pooler host, port 6543."""
        config = _database_from_url(
            'postgresql://postgres.myref:secret123@'
            'aws-0-eu-central-1.pooler.supabase.com:6543/postgres'
        )
        self.assertEqual(config['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(config['NAME'], 'postgres')
        self.assertEqual(config['USER'], 'postgres.myref')
        self.assertEqual(config['PASSWORD'], 'secret123')
        self.assertEqual(
            config['HOST'], 'aws-0-eu-central-1.pooler.supabase.com'
        )
        self.assertEqual(config['PORT'], '6543')
        # No sslmode in the URL -> SSL still required, never plaintext.
        self.assertEqual(config['OPTIONS'], {'sslmode': 'require'})

    def test_direct_url(self):
        """Supabase's direct form: db.<ref> host, port 5432."""
        config = _database_from_url(
            'postgresql://postgres:secret123@db.myref.supabase.co:5432/postgres'
        )
        self.assertEqual(config['HOST'], 'db.myref.supabase.co')
        self.assertEqual(config['PORT'], '5432')

    def test_postgres_scheme_spelling(self):
        """postgres:// (no 'ql') is the same thing, older spelling."""
        config = _database_from_url(
            'postgres://postgres:secret123@db.myref.supabase.co:5432/postgres'
        )
        self.assertEqual(config['ENGINE'], 'django.db.backends.postgresql')

    def test_explicit_sslmode_is_respected(self):
        """A sslmode written in the URL wins over the default."""
        config = _database_from_url(
            'postgresql://postgres:secret123@db.myref.supabase.co:5432/'
            'postgres?sslmode=verify-full'
        )
        self.assertEqual(config['OPTIONS'], {'sslmode': 'verify-full'})

    def test_url_encoded_password_is_decoded(self):
        """Supabase passwords with % or @ must be escaped in a URL."""
        config = _database_from_url(
            'postgresql://postgres:p%40ss%25word@'
            'db.myref.supabase.co:5432/postgres'
        )
        self.assertEqual(config['PASSWORD'], 'p@ss%word')

    def test_non_postgres_scheme_rejected(self):
        """A MySQL (or anything else) URL is a loud error, not a guess."""
        with self.assertRaises(ValueError):
            _database_from_url('mysql://user:pass@host:3306/db')


class DatabaseEnvWiringTests(SimpleTestCase):
    def test_unset_database_url_keeps_sqlite(self):
        """Default behaviour, unchanged: no variable -> SQLite file."""
        self.assertEqual(
            _engine_with_env(None), 'django.db.backends.sqlite3'
        )

    def test_dummy_postgres_url_resolves_to_postgres(self):
        """A dummy URL must resolve to the Postgres backend at import
        time without crashing — no live server is contacted here, the
        engine string is all we check."""
        self.assertEqual(
            _engine_with_env(
                'postgresql://postgres:secret123@'
                'aws-0-eu-central-1.pooler.supabase.com:6543/postgres'
            ),
            'django.db.backends.postgresql',
        )
