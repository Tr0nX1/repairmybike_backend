import os
import django
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from vehicles.models import VehicleBrand

def create_test_image():
    # Create a 100x100 red image
    file = BytesIO()
    image = Image.new('RGB', (100, 100), color='red')
    image.save(file, 'png')
    file.name = 'test_cloud_upload.png'
    file.seek(0)
    return file

def test_upload():
    print("🚀 Starting Cloudinary Upload Test...")
    
    # helper
    from django.conf import settings
    print(f"🔧 USE_CLOUDINARY: {settings.USE_CLOUDINARY}")
    print(f"🔧 MEDIA_URL: {settings.MEDIA_URL}")
    print(f"🔧 DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
    print(f"🔧 CLOUDINARY_STORAGE: {getattr(settings, 'CLOUDINARY_STORAGE', 'NOT SET')}")
    print(f"🔧 Env CLOUDINARY_URL: {os.environ.get('CLOUDINARY_URL', 'NOT SET')}")

    # Get a brand to update
    brand = VehicleBrand.objects.first()
    if not brand:
        print("❌ No Vehicle Brand found. Creating one...")
        brand = VehicleBrand.objects.create(name="Test Brand", description="Created for testing")
    
    print(f"📸 Updating Brand: {brand.name}")
    
    # Create image
    img_io = create_test_image()
    
    # Save the image content
    # save() method on ImageField automatically uploads to storage backend
    brand.image.save('test_brand_logo.png', ContentFile(img_io.getvalue()), save=True)
    
    print(f"✅ Upload Complete!")
    print(f"🔗 New Image URL: {brand.image.url}")
    
    if "cloudinary.com" in brand.image.url:
        print("🎉 SUCCESS: Image is hosted on Cloudinary.")
    elif "res.cloudinary.com" in brand.image.url:
        print("🎉 SUCCESS: Image is hosted on Cloudinary.") 
    else:
        print("⚠️ WARNING: URL does not look like Cloudinary. Check settings.")

if __name__ == "__main__":
    try:
        test_upload()
    except Exception as e:
        print(f"❌ ERROR: {e}")
