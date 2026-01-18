
import os
import django
from django.core.files import File
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from django.conf import settings
from vehicles.models import VehicleType, VehicleBrand, VehicleModel
from spare_parts.models import SparePartImage, SparePartBrand, SparePartCategory
from services.models import Service
from subscriptions.models import Plan

MODELS_TO_MIGRATE = [
    (VehicleType, 'image'),
    (VehicleBrand, 'image'),
    (VehicleModel, 'image'),
    (Plan, 'image'),
    (SparePartImage, 'image'),
    (SparePartBrand, 'logo'),
    (SparePartCategory, 'image'),
    (Service, 'images'),
]

BASE_DIR = settings.BASE_DIR
MEDIA_ROOT = settings.MEDIA_ROOT

def get_local_path(db_path):
    """
    Try to find the file in common locations.
    """
    # 1. Direct path inside MEDIA_ROOT
    p1 = Path(MEDIA_ROOT) / db_path
    if p1.exists() and p1.is_file():
        return p1

    # 2. If path starts with 'media/', try removing it (common redundancy)
    if db_path.startswith('media/') or db_path.startswith('media\\'):
        clean_path = db_path.replace('media/', '').replace('media\\', '')
        p2 = Path(MEDIA_ROOT) / clean_path
        if p2.exists() and p2.is_file():
            return p2
            
    # 3. Check relative to BASE_DIR (if MEDIA_ROOT was misconfigured previously)
    p3 = BASE_DIR / db_path
    if p3.exists() and p3.is_file():
        return p3

    return None

def migrate_model(model, field_name):
    print(f"\n--- Migrating {model.__name__} ---")
    qs = model.objects.exclude(**{f'{field_name}__startswith': 'http'}).exclude(**{f'{field_name}': ''})
    
    success_count = 0
    fail_count = 0
    
    for obj in qs:
        db_path = str(getattr(obj, field_name))
        local_file = get_local_path(db_path)
        
        if local_file:
            print(f"Processing ID {obj.id}: {local_file.name}")
            try:
                with open(local_file, 'rb') as f:
                    # Save to the field. This triggers the storage backend (Cloudinary)
                    # We pass the filename to ensure it uses the correct name/extension
                    getattr(obj, field_name).save(local_file.name, File(f), save=True)
                    print(f"  ✅ Uploaded & Updated: {getattr(obj, field_name)}")
                    success_count += 1
            except Exception as e:
                print(f"  ❌ Error uploading: {e}")
                fail_count += 1
        else:
            print(f"  ⚠️  File NOT found for ID {obj.id}: {db_path}")
            fail_count += 1

    print(f"{model.__name__}: {success_count} success, {fail_count} failed.")

if __name__ == '__main__':
    print("Starting Legacy Media Migration to Cloudinary...")
    for model, field in MODELS_TO_MIGRATE:
        migrate_model(model, field)
    print("\nMigration Complete.")
