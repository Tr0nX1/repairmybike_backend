import os
import django
import sys

# Set encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from services.models import Service, ServiceCategory
from shop.models import ShopInfo
from spare_parts.models import SparePart

def check_images():
    print("--- Services ---")
    services = Service.objects.all()[:5]
    for s in services:
        print(f"Service: {s.name}")
        if s.images:
            try:
                print(f"  Image URL: {s.images.url}")
            except Exception as e:
                print(f"  Error getting URL: {e}")
        else:
            print("  No image field")
            
    print("\n--- Categories ---")
    categories = ServiceCategory.objects.all()[:5]
    for c in categories:
        print(f"Category: {c.name}")
        # Categories don't seem to have images in the model I saw earlier, but let's check
        # Wait, Category has an 'icon' field which is a string.

    print("\n--- Spare Parts ---")
    parts = SparePart.objects.all()[:5]
    for p in parts:
        print(f"Part: {p.name}")
        if hasattr(p, 'image') and p.image:
             try:
                print(f"  Image URL: {p.image.url}")
             except Exception as e:
                print(f"  Error getting URL: {e}")
        else:
            print("  No image field")

if __name__ == "__main__":
    check_images()
