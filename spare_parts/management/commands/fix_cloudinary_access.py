from django.core.management.base import BaseCommand
import cloudinary
import cloudinary.api
from django.conf import settings

class Command(BaseCommand):
    help = 'Fix Cloudinary image access mode for spare parts and other media'
    
    def handle(self, *args, **options):
        if not settings.USE_CLOUDINARY:
            self.stdout.write(self.style.WARNING('Cloudinary is not enabled. Skipping.'))
            return

        self.stdout.write('Fetching authenticated resources from Cloudinary...')
        
        try:
            # We look for ALL authenticated resources, not just spare_parts
            # since the 424 bug might affect categories or brands too.
            result = cloudinary.api.resources(
                type='authenticated',
                max_results=500
            )
            
            resources = result.get('resources', [])
            if not resources:
                self.stdout.write(self.style.SUCCESS('No authenticated resources found.'))
                return

            self.stdout.write(f'Found {len(resources)} authenticated resources. Converting to public...')
            
            for resource in resources:
                public_id = resource['public_id']
                resource_type = resource.get('resource_type', 'image')
                
                self.stdout.write(f'Fixing: {public_id} ({resource_type})...', ending='')
                
                try:
                    # Update access_mode to public and type to upload
                    # Note: cloudinary-django usually handles the 'upload' type by default
                    # but we need to ensure the existing ones are reachable.
                    cloudinary.api.update(
                        public_id,
                        resource_type=resource_type,
                        type='upload',
                        access_mode='public'
                    )
                    self.stdout.write(self.style.SUCCESS(' OK'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f' FAILED: {str(e)}'))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Critical error communicating with Cloudinary: {str(e)}'))
