"""
Django management command to wait for database to be available.
This is particularly useful for Railway deployments where the database
might not be immediately available when the application starts.
"""
import time
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    """Django command to wait for database to be available."""
    
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
            help='Time to wait between connection attempts (seconds)'
        )
    
    def handle(self, *args, **options):
        """Handle the command execution."""
        timeout = options['timeout']
        interval = options['interval']
        
        self.stdout.write('Waiting for database...')
        
        start_time = time.time()
        db_conn = None
        
        while time.time() - start_time < timeout:
            try:
                db_conn = connections['default']
                db_conn.cursor()
                break
            except OperationalError:
                self.stdout.write(
                    f'Database unavailable, waiting {interval} second(s)...'
                )
                time.sleep(interval)
        else:
            self.stdout.write(
                self.style.ERROR(
                    f'Database unavailable after {timeout} seconds!'
                )
            )
            raise OperationalError('Database connection timeout')
        
        self.stdout.write(
            self.style.SUCCESS('Database available!')
        )