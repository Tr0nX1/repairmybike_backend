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


class StatusColorMixin:
    """Mixin to provide colored status badges in the admin list view."""

    def _get_status_color(self, status):
        """Map status values to colors."""
        status = str(status).lower()
        
        # Success / Positive
        if status in ['paid', 'confirmed', 'completed', 'active', 'delivered', 'dispatched', 'verified', 'success']:
            return '#28a745'  # Green
        
        # Warning / Neutral
        if status in ['pending', 'processing', 'ongoing', 'partial', 'shipped', 'warning']:
            return '#ffc107'  # Amber
        
        # Danger / Negative
        if status in ['failed', 'cancelled', 'cancelled_by_user', 'cancelled_by_staff', 'inactive', 'unpaid', 'out_of_stock', 'rejected', 'error']:
            return '#dc3545'  # Red
        
        return '#6c757d'  # Grey fallback

    def colored_status(self, obj, field_name='status'):
        """Generic method to render a colored status badge."""
        status = getattr(obj, field_name, 'Unknown')
        color = self._get_status_color(status)
        
        return format_html(
            '<span style="background-color: {0}; color: white; padding: 4px 10px; '
            'border-radius: 12px; font-weight: bold; font-size: 0.85em; text-transform: uppercase;">'
            '{1}'
            '</span>',
            color,
            status
        )
