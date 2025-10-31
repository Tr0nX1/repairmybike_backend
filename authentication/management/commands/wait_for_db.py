"""
Django command to wait for the database to be available.
"""
import time
from psycopg2 import OperationalError as Psycopg2OpError
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import ConnectionHandler


class Command(BaseCommand):
    """Django command to wait for database."""

    help = 'Wait for database to be available'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Maximum time to wait for database (seconds)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=1,
            help='Time between connection attempts (seconds)'
        )

    def handle(self, *args, **options):
        """Entrypoint for command."""
        timeout = options['timeout']
        interval = options['interval']
        
        self.stdout.write('Waiting for database...')
        
        start_time = time.time()
        db_conn = None
        
        while time.time() - start_time < timeout:
            try:
                # Try to get the default database connection
                db_conn = connections['default']
                
                # Test the connection
                with db_conn.cursor() as cursor:
                    cursor.execute('SELECT 1')
                
                self.stdout.write(
                    self.style.SUCCESS('Database available!')
                )
                return
                
            except (Psycopg2OpError, OperationalError) as e:
                self.stdout.write(
                    f'Database unavailable, waiting {interval} second(s)... ({str(e)[:50]})'
                )
                time.sleep(interval)
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Unexpected error: {str(e)[:100]}')
                )
                time.sleep(interval)
        
        # If we get here, we've timed out
        self.stdout.write(
            self.style.ERROR(
                f'Database unavailable after {timeout} seconds. '
                'Application may not work correctly.'
            )
        )
        # Don't exit with error code - let the application try to start anyway