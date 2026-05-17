import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from django.db import connection

def fix_services_columns():
    columns_to_check = [
        ('rating', 'decimal(3,2) DEFAULT 0'),
        ('reviews_count', 'integer DEFAULT 0'),
        ('specifications', 'jsonb DEFAULT \'[]\'::jsonb'),
        ('images', 'varchar(100)'),
        ('is_featured', 'boolean DEFAULT false'),
    ]
    with connection.cursor() as cursor:
        for col_name, col_type in columns_to_check:
            print(f"Checking for column '{col_name}' in table 'services'...")
            cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='services' AND column_name='{col_name}';")
            if not cursor.fetchone():
                print(f"Column '{col_name}' missing. Adding it now...")
                cursor.execute(f"ALTER TABLE services ADD COLUMN {col_name} {col_type};")
                print(f"Column '{col_name}' added successfully.")
            else:
                print(f"Column '{col_name}' already exists.")

if __name__ == "__main__":
    fix_services_columns()
