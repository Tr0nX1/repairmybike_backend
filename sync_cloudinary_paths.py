import os
import sys
import django
import argparse
from difflib import SequenceMatcher

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')

django.setup()

import cloudinary
import cloudinary.api
from django.conf import settings
from spare_parts.models import SparePartImage, SparePartBrand, SparePartCategory
from vehicles.models import VehicleBrand, VehicleModel, VehicleType
from services.models import Service


def similarity_ratio(a, b):
    """Calculate similarity between two strings (0-1)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def extract_base_filename(path):
    """Extract the base filename without path, extension, or Cloudinary suffix"""
    # Remove path
    filename = path.split('/')[-1]
    # Remove extension
    filename = filename.rsplit('.', 1)[0]
    # Remove Cloudinary suffix (underscore + random chars at end)
    if '_' in filename:
        parts = filename.rsplit('_', 1)
        # Check if last part looks like a Cloudinary hash (6+ chars, alphanumeric)
        if len(parts[1]) >= 6 and parts[1].isalnum():
            filename = parts[0]
    return filename


def find_best_match(db_path, cloudinary_resources):
    """Find the best matching Cloudinary resource for a database path"""
    db_base = extract_base_filename(db_path)
    
    best_match = None
    best_score = 0.0
    
    for resource in cloudinary_resources:
        # Get public_id without 'media/' prefix if present
        public_id = resource['public_id']
        if public_id.startswith('media/'):
            public_id = public_id[6:]  # Remove 'media/' prefix
        
        cloud_base = extract_base_filename(public_id)
        
        # Calculate similarity
        score = similarity_ratio(db_base, cloud_base)
        
        # Bonus points if folder matches
        db_folder = '/'.join(db_path.split('/')[:-1])
        cloud_folder = '/'.join(public_id.split('/')[:-1])
        if db_folder == cloud_folder:
            score += 0.2
        
        if score > best_score and score > 0.6:  # Minimum 60% similarity
            best_score = score
            best_match = resource
    
    return best_match, best_score


def sync_model_images(model, field_name, cloudinary_resources, dry_run=False, verbose=False):
    """Sync image paths for a specific model and field"""
    print(f"\n{'='*60}")
    print(f"Syncing {model.__name__}.{field_name}")
    print(f"{'='*60}")
    
    updated_count = 0
    skipped_count = 0
    
    for obj in model.objects.all():
        field = getattr(obj, field_name)
        if not field or not field.name:
            continue
        
        db_path = field.name
        
        # Find matching Cloudinary resource
        match, score = find_best_match(db_path, cloudinary_resources)
        
        if match:
            # Get public_id without 'media/' prefix
            new_path = match['public_id']
            if new_path.startswith('media/'):
                new_path = new_path[6:]
            
            full_url = match.get('secure_url')
            
            # Check if we need to update either the path or the explicit cloudinary_url field
            needs_update = False
            
            if new_path != db_path:
                needs_update = True
                print(f"\n  📝 {obj} (ID: {obj.id}) - Path change")
                print(f"     Old Path: {db_path}")
                print(f"     New Path: {new_path}")
            
            # If the model has a cloudinary_url field, check it
            if hasattr(obj, 'cloudinary_url') and obj.cloudinary_url != full_url:
                needs_update = True
                if not verbose and new_path == db_path: # Print header if it wasn't printed above
                    print(f"\n  📝 {obj} (ID: {obj.id}) - URL sync")
                print(f"     Old URL: {obj.cloudinary_url}")
                print(f"     New URL: {full_url}")

            if needs_update:
                if not dry_run:
                    field.name = new_path
                    if hasattr(obj, 'cloudinary_url'):
                        obj.cloudinary_url = full_url
                    obj.save()
                    print(f"     ✅ Updated")
                else:
                    print(f"     🔍 Would update (dry-run)")
                updated_count += 1
            else:
                skipped_count += 1
                if verbose:
                    print(f"  ✓ {obj}: Already synced")
        else:
            print(f"  ⚠️  No match found for: {db_path} (in {obj})")
    
    print(f"\n  Summary: {updated_count} updated, {skipped_count} already synced")
    return updated_count, skipped_count


def main():
    parser = argparse.ArgumentParser(description='Sync database image paths with Cloudinary')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying them')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print detailed information')
    args = parser.parse_args()
    
    print("="*60)
    print("Cloudinary Database Sync Script")
    print("="*60)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")
    
    # Configure Cloudinary
    cloudinary_url = settings.CLOUDINARY_STORAGE.get('CLOUDINARY_URL')
    if cloudinary_url:
        os.environ['CLOUDINARY_URL'] = cloudinary_url
    
    print("Fetching resources from Cloudinary...")
    
    # Fetch all resources from Cloudinary
    all_resources = []
    next_cursor = None
    
    try:
        while True:
            result = cloudinary.api.resources(
                type='upload',
                max_results=500,
                next_cursor=next_cursor
            )
            all_resources.extend(result['resources'])
            next_cursor = result.get('next_cursor')
            
            print(f"  Fetched {len(all_resources)} resources...", end='\r')
            
            if not next_cursor:
                break
        
        print(f"\n✅ Found {len(all_resources)} resources on Cloudinary\n")
    
    except Exception as e:
        print(f"\n❌ Error fetching Cloudinary resources: {e}")
        print("Make sure CLOUDINARY_URL is properly configured in .env")
        sys.exit(1)
    
    # Sync each model
    total_updated = 0
    total_skipped = 0
    
    models_to_sync = [
        (SparePartImage, 'image'),
        (SparePartBrand, 'logo'),
        (SparePartCategory, 'image'),
        (VehicleBrand, 'image'),
        (VehicleModel, 'image'),
        (VehicleType, 'image'),
        (Service, 'images'),
    ]
    
    for model, field_name in models_to_sync:
        updated, skipped = sync_model_images(model, field_name, all_resources, args.dry_run, args.verbose)
        total_updated += updated
        total_skipped += skipped
    
    # Final summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Total updated: {total_updated}")
    print(f"Total already synced: {total_skipped}")
    
    if args.dry_run:
        print("\n🔍 This was a DRY RUN. Run without --dry-run to apply changes.")
    else:
        print("\n✅ Database sync complete!")
        print("\nNext steps:")
        print("1. Test image loading in your Flutter app")
        print("2. Check for any remaining 404 errors")
        print("3. Run 'python audit_media.py' to verify sync")


if __name__ == '__main__':
    main()
