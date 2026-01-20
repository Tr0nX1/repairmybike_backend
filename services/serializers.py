from rest_framework import serializers
from django.conf import settings
from .models import ServiceCategory, Service, ServicePricing, UserSavedService, GuestSavedService

# Removed build_absolute_media_url - using storage backend directly

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
        """Returns absolute URLs from storage backend.
        Supports:
        - Single ImageField on Service (obj.images)
        - Related ServiceImage objects via obj.images.all()
        - Backward compatibility: Return empty list for old data
        """
        raw = getattr(obj, 'images', None)
        if not raw:
            return []

        # Case 1: ImageField on Service - Use storage backend directly
        try:
            if hasattr(raw, 'url'):
                return [raw.url] if getattr(raw, 'name', None) else []
        except Exception:
            pass

        # Case 2: Related images manager (future-proof) - Use storage backend
        if hasattr(raw, 'all'):
            urls = []
            for item in raw.all():
                img = getattr(item, 'image', None)
                if img and getattr(img, 'name', None):
                    try:
                        urls.append(img.url)  # ✅ Storage backend generates URL
                    except Exception:
                        continue
            return urls

        # Case 3: Backward compatibility - old string data is invalid now
        # Return empty to trigger re-upload via admin
        return []


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


class UserSavedServiceSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(), source='service', write_only=True
    )

    class Meta:
        model = UserSavedService
        fields = ['id', 'service', 'service_id', 'created_at']
        read_only_fields = ['id', 'created_at']


class GuestSavedServiceSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(), source='service', write_only=True
    )

    class Meta:
        model = GuestSavedService
        fields = ['id', 'service', 'service_id', 'created_at']
        read_only_fields = ['id', 'created_at']