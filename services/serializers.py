from rest_framework import serializers
from django.conf import settings
from .models import ServiceCategory, Service, ServicePricing, UserSavedService, GuestSavedService

# Removed build_absolute_media_url - using storage backend directly




class ServiceCategorySerializer(serializers.ModelSerializer):
    service_count = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    
    def get_service_count(self, obj):
        return obj.get_service_count()
    
    def get_image(self, obj):
        """Returns standardized media object from storage backend."""
        if not obj.image:
            return None
        try:
            url = obj.image.url
            return {
                "thumbnail": url,
                "original": url,
                "alt_text": obj.name
            }
        except Exception:
            return None

    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'description', 'icon', 'image', 'service_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='service_category.name', read_only=True)
    price = serializers.SerializerMethodField()
    original_price = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    
    def get_price(self, obj):
        # Get the lowest price across all vehicle models
        pricing = obj.pricing.order_by('price').first()
        return float(pricing.price) if pricing else 0.0

    def get_original_price(self, obj):
        pricing = obj.pricing.order_by('price').first()
        return float(pricing.original_price) if pricing and pricing.original_price else None
    
    class Meta:
        model = Service
        fields = [
            'id', 'service_category', 'category_name', 'name', 'description',
            'rating', 'reviews_count', 'specifications', 'images', 'price', 'original_price',
            'is_featured', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_images(self, obj):
        """Returns standardized media objects from storage backend."""
        images = []
        raw = getattr(obj, 'images', None)
        if not raw:
            return []

        # Case 1: ImageField on Service
        if hasattr(raw, 'name') and raw.name:
            try:
                url = raw.url
                images.append({
                    "thumbnail": url,
                    "original": url,
                    "alt_text": obj.name
                })
            except Exception:
                pass

        # Case 2: Related images manager (future-proof)
        if hasattr(raw, 'all'):
            for item in raw.all():
                img = getattr(item, 'image', None)
                if img and getattr(img, 'name', None):
                    try:
                        urls = img.url
                        images.append({
                            "thumbnail": urls,
                            "original": urls,
                            "alt_text": getattr(item, 'alt_text', f"Image for {obj.name}")
                        })
                    except Exception:
                        continue
        
        return images


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
            'description', 'vehicle_model', 'original_price', 'price', 'created_at', 'updated_at'
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