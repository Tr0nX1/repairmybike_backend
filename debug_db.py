import django
from django.db import connection
import sys

# Set encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

def dump_columns(table_name):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}'")
        columns = cursor.fetchall()
        print(f"\nColumns for {table_name}:")
        for col in columns:
            print(f" - {col[0]} ({col[1]})")

def show_applied_migrations():
    with connection.cursor() as cursor:
        cursor.execute("SELECT app, name, applied FROM django_migrations WHERE app = 'subscriptions' ORDER BY applied")
        migrations = cursor.fetchall()
        print(f"\nApplied migrations for 'subscriptions':")
        for mig in migrations:
            print(f" - {mig[1]} (Applied at {mig[2]})")

if __name__ == "__main__":
    dump_columns('subscriptions_plan')
    show_applied_migrations()
