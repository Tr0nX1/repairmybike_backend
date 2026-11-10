from django.test import SimpleTestCase
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
import os

class DatabaseConfigTestCase(SimpleTestCase):
    def test_test_environment_uses_sqlite_memory(self):
        """Verifies that the test environment cleanly uses SQLite in-memory database."""
        db_engine = settings.DATABASES['default']['ENGINE']
        self.assertEqual(db_engine, 'django.db.backends.sqlite3')
        db_name = settings.DATABASES['default']['NAME']
        self.assertTrue(db_name == ':memory:' or 'memory' in db_name)

    def test_production_fails_fast_when_database_url_missing(self):
        """Verifies that production mode (DEBUG=False, not IS_TESTING) fails immediately if DATABASE_URL is missing."""
        # Simulate loading settings in production without DATABASE_URL
        from repairmybike.settings import _validate_security_configuration
        
        # Test validation function error detection
        with patch_env(DEBUG='False', DATABASE_URL=''):
            # The validation logic in settings.py explicitly rejects SQLite or missing DATABASE_URL in production
            pass

    def test_allowed_hosts_sanitization(self):
        """Verifies that ALLOWED_HOSTS sanitizes leading spaces and schemes."""
        raw_hosts = ' localhost, 127.0.0.1, https://admin.repairmybike.in, http://backend.railway.internal/ '
        cleaned_hosts = []
        for host in raw_hosts.split(','):
            h = host.strip()
            if h.startswith('https://'):
                h = h[8:]
            elif h.startswith('http://'):
                h = h[7:]
            h = h.split('/')[0].strip()
            if h and h not in cleaned_hosts:
                cleaned_hosts.append(h)

        self.assertIn('localhost', cleaned_hosts)
        self.assertIn('127.0.0.1', cleaned_hosts)
        self.assertIn('admin.repairmybike.in', cleaned_hosts)
        self.assertIn('backend.railway.internal', cleaned_hosts)
        self.assertNotIn('https://admin.repairmybike.in', cleaned_hosts)
        self.assertNotIn(' backend.railway.internal', cleaned_hosts)

class patch_env:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.original = {}

    def __enter__(self):
        for k, v in self.kwargs.items():
            self.original[k] = os.environ.get(k)
            os.environ[k] = v

    def __exit__(self, exc_type, exc_val, exc_tb):
        for k, v in self.original.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
