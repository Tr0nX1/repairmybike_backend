from django.core.management.base import BaseCommand
from spare_parts.models import SparePart, SparePartImage

class Command(BaseCommand):
    help = 'Clear broken Cloudinary image references'
    
    def handle(self, *args, **options):
        cleared = 0
        
        # Check SparePart thumbnails
        for part in SparePart.objects.filter(thumbnail__isnull=False):
            url = str(part.thumbnail)
            # If it's a local path not a full URL and not a Cloudinary handle
            if not url.startswith('http') and not url.startswith('spare_parts/'):
                self.stdout.write(f'Clearing broken thumbnail for: {part.name} ({url})')
                part.thumbnail = None
                part.save()
                cleared += 1
        
        # Check SparePartImage images
        for img in SparePartImage.objects.filter(image__isnull=False):
            url = str(img.image)
            if not url.startswith('http') and not url.startswith('spare_parts/'):
                self.stdout.write(f'Clearing broken image for part: {img.spare_part.name} ({url})')
                img.image = None
                img.save()
                cleared += 1
        
        self.stdout.write(self.style.SUCCESS(f'Cleared {cleared} broken image references'))
