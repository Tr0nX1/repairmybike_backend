from rest_framework import serializers
from django.conf import settings
from .models import ServiceCategory, Service, ServicePricing
try:
    from cloudinary.utils import cloudinary_url as _cloudinary_url
except Exception:
    _cloudinary_url = None


class ServiceCategorySerializer(serializers.ModelSerializer):
    service_count = serializers.SerializerMethodField()
    
    def get_service_count(self, obj):
        return obj.get_service_count()
    
    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'description', 'icon', 'service_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='service_category.name', read_only=True)
    price = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    
    def get_price(self, obj):
        # Get the lowest price across all vehicle models
        pricing = obj.pricing.order_by('price').first()
        return float(pricing.price) if pricing else 0.0
    
    class Meta:
        model = Service
        fields = [
            'id', 'service_category', 'category_name', 'name', 'description',
            'rating', 'reviews_count', 'specifications', 'images', 'price',
            'is_featured', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_images(self, obj):
        """Return a sanitized list of image URLs.
        - Accepts both list and single string (in case models changed).
        - Filters out non-image-like strings (e.g., description text).
        - Normalizes to absolute URLs when possible (Cloudinary or MEDIA_URL).
        """
        raw = getattr(obj, 'images', None)
        # Normalize raw to list
        if raw is None:
            imgs = []
        elif isinstance(raw, list):
            imgs = raw
        else:
            imgs = [str(raw)]

        # Helper: quick heuristic to decide whether a string is image-like
        def _is_image_like(s: str) -> bool:
            if not s:
                return False
            t = s.strip().lower()
            if t.startswith('http://') or t.startswith('https://') or t.startswith('data:image/'):
                return True
            if t.startswith('/') or t.startswith('media/'):
                return True
            # filename extension check
            for ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'):
                if t.endswith(ext):
                    return True
            return False

        imgs = [str(u) for u in imgs if _is_image_like(str(u))]

        # Prefer Cloudinary when enabled, but preserve existing local paths
        if getattr(settings, 'USE_CLOUDINARY', False) and _cloudinary_url:
            def _to_abs_cloudinary_or_local(u: str):
                if not u:
                    return None
                u = u.strip()
                if u.startswith('http://') or u.startswith('https://') or u.startswith('data:image/'):
                    return u
                # Local media path
                if u.startswith('/') or 'media/' in u or u.startswith('media/'):
                    base_local = getattr(settings, 'MEDIA_URL', '/')
                    if base_local.startswith('http://') or base_local.startswith('https://'):
                        if u.startswith('/'):
                            return f"{base_local.rstrip('/')}{u}"
                        return f"{base_local.rstrip('/')}/{u}"
                    return u  # relative fallback
                # Otherwise treat as Cloudinary public ID
                return _cloudinary_url(u)[0]

            return [x for x in (_to_abs_cloudinary_or_local(u) for u in imgs) if x]

        # Fallback to joining with MEDIA_URL (R2/local)
        base = getattr(settings, 'MEDIA_URL', '/')

        def _to_abs(u: str):
            if not u:
                return None
            u = u.strip()
            if u.startswith('http://') or u.startswith('https://') or u.startswith('data:image/'):
                return u
            if base.startswith('http://') or base.startswith('https://'):
                # Ensure single slash join
                if u.startswith('/'):
                    return f"{base.rstrip('/')}{u}"
                return f"{base.rstrip('/')}/{u}"
            # Fallback: return as-is
            return u

        return [x for x in (_to_abs(u) for u in imgs) if x]


class ServicePricingSerializer(serializers.ModelSerializer):
    service_id = serializers.IntegerField(source='service.id', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    category_id = serializers.IntegerField(source='service.service_category.id', read_only=True)
    category_name = serializers.CharField(source='service.service_category.name', read_only=True)
    description = serializers.CharField(source='service.description', read_only=True)
    
    class Meta:
        model = ServicePricing
        fields = [
            'id', 'service_id', 'service_name', 'category_id', 'category_name',
            'description', 'vehicle_model', 'price', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']