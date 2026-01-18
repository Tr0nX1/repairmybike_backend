import os
import django
import sys
from django.db import connection

# Set encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

def audit_subscriptions():
    with connection.cursor() as cursor:
        # 1. Check columns in subscriptions_plan
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'subscriptions_plan'
        """)
        columns = cursor.fetchall()
        print("\n--- Columns in 'subscriptions_plan' ---")
        for col in columns:
            print(f" - {col[0]} ({col[1]})")

        # 2. Check for data in 'image' column if it exists
        col_names = [col[0] for col in columns]
        if 'image' in col_names:
            cursor.execute("SELECT COUNT(*) FROM subscriptions_plan WHERE image IS NOT NULL AND image != ''")
            count = cursor.fetchone()[0]
            print(f"\nRow count with non-empty 'image': {count}")
        else:
            print("\n'image' column NOT found in DB.")

        # 3. Check migration history
        cursor.execute("SELECT name, applied FROM django_migrations WHERE app = 'subscriptions' ORDER BY name")
        migrations = cursor.fetchall()
        print("\n--- Migration History (DB) ---")
        for mig in migrations:
            print(f" - {mig[0]} (Applied at {mig[1]})")

if __name__ == "__main__":
    audit_subscriptions()
