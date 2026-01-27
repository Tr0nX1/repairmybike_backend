"""
Test script to verify the spare parts API returns correct thumbnail format.

Run this from the backend directory:
    python test_spare_parts_api.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from spare_parts.models import SparePart
from spare_parts.serializers import SparePartListSerializer

def test_thumbnail_format():
    print("Testing Spare Parts API thumbnail format...\n")
    
    # Get a spare part with images
    parts_with_images = SparePart.objects.filter(images__isnull=False, active=True).distinct()[:3]
    
    if not parts_with_images.exists():
        print("❌ No spare parts with images found in database")
        return
    
    print(f"Found {parts_with_images.count()} spare parts with images\n")
    
    for part in parts_with_images:
        serializer = SparePartListSerializer(part)
        data = serializer.data
        
        print(f"Part: {data['name']}")
        print(f"SKU: {data['sku']}")
        print(f"Thumbnail type: {type(data['thumbnail'])}")
        print(f"Thumbnail value: {data['thumbnail']}")
        
        # Verify thumbnail is a string URL, not a dict
        if isinstance(data['thumbnail'], str):
            print("✅ PASS: Thumbnail is a string URL")
        elif data['thumbnail'] is None:
            print("⚠️  WARNING: Thumbnail is None (no image)")
        else:
            print(f"❌ FAIL: Thumbnail is {type(data['thumbnail'])}, expected string")
        
        print("-" * 60)
    
    # Test the full API response format
    print("\nTesting full list response format...")
    parts = SparePart.objects.filter(active=True)[:2]
    serializer = SparePartListSerializer(parts, many=True)
    
    print(f"Response type: {type(serializer.data)}")
    print(f"Number of parts: {len(serializer.data)}")
    
    if serializer.data:
        first_part = serializer.data[0]
        print(f"\nFirst part structure:")
        print(f"  - id: {first_part.get('id')}")
        print(f"  - name: {first_part.get('name')}")
        print(f"  - thumbnail: {first_part.get('thumbnail')}")
        print(f"  - thumbnail type: {type(first_part.get('thumbnail'))}")
        
        if isinstance(first_part.get('thumbnail'), str) or first_part.get('thumbnail') is None:
            print("\n✅ SUCCESS: API response format is correct!")
        else:
            print("\n❌ FAILURE: API response format is incorrect!")

if __name__ == '__main__':
    test_thumbnail_format()
