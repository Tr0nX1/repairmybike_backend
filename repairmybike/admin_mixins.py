from django.utils.html import format_html
from django.conf import settings

class ImagePreviewMixin:
    """Mixin to add image preview functionality to ModelAdmin classes"""
    
    def image_preview(self, obj):
        # Try to find an image field
        # We check common names: 'image', 'logo', 'icon'
        image_field = None
        for attr in ['image', 'logo', 'icon', 'images']:
            if hasattr(obj, attr):
                val = getattr(obj, attr)
                # If it's a list (like in Services), take the first one
                if isinstance(val, list) and val:
                    image_field = val[0]
                    break
                elif val:
                    image_field = val
                    break
        
        if image_field:
            try:
                url = image_field.url if hasattr(image_field, 'url') else str(image_field)
                if url:
                    return format_html(
                        '<a href="{0}" target="_blank"><img src="{0}" style="max-height: 100px; max-width: 100px; border-radius: 8px; border: 1px solid #ddd;" /></a>',
                        url
                    )
            except Exception:
                pass
        return "No Image"

    image_preview.short_description = 'Preview'
