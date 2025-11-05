from rest_framework import serializers
from django.conf import settings
from .models import VehicleType, VehicleBrand, VehicleModel


class VehicleTypeSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    class Meta:
        model = VehicleType
        fields = ['id', 'name', 'image', 'created_at', 'updated_at']  # ✅ added image
        read_only_fields = ['id', 'created_at', 'updated_at']

    def _abs_url(self, url: str):
        if not url:
            return None
        if url.startswith('http://') or url.startswith('https://'):
            return url
        request = self.context.get('request') if hasattr(self, 'context') else None
        if request:
            try:
                return request.build_absolute_uri(url)
            except Exception:
                pass
        base = getattr(settings, 'MEDIA_URL', '/')
        if base.startswith('http://') or base.startswith('https://'):
            if url.startswith('/'):
                return f"{base.rstrip('/')}{url}"
            return f"{base.rstrip('/')}/{url}"
        return url

    def get_image(self, obj):
        try:
            return self._abs_url(obj.image.url) if obj.image else None
        except Exception:
            return None


class VehicleBrandSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    vehicle_type_name = serializers.CharField(source='vehicle_type.name', read_only=True)
    
    class Meta:
        model = VehicleBrand
        fields = ['id', 'vehicle_type', 'vehicle_type_name', 'name', 'image', 'created_at', 'updated_at']  # ✅ added image
        read_only_fields = ['id', 'created_at', 'updated_at']

    def _abs_url(self, url: str):
        if not url:
            return None
        if url.startswith('http://') or url.startswith('https://'):
            return url
        request = self.context.get('request') if hasattr(self, 'context') else None
        if request:
            try:
                return request.build_absolute_uri(url)
            except Exception:
                pass
        base = getattr(settings, 'MEDIA_URL', '/')
        if base.startswith('http://') or base.startswith('https://'):
            if url.startswith('/'):
                return f"{base.rstrip('/')}{url}"
            return f"{base.rstrip('/')}/{url}"
        return url

    def get_image(self, obj):
        try:
            return self._abs_url(obj.image.url) if obj.image else None
        except Exception:
            return None


class VehicleModelSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    brand_name = serializers.CharField(source='vehicle_brand.name', read_only=True)
    vehicle_type_name = serializers.CharField(source='vehicle_brand.vehicle_type.name', read_only=True)
    
    class Meta:
        model = VehicleModel
        fields = ['id', 'vehicle_brand', 'brand_name', 'vehicle_type_name', 'name', 'image', 'created_at', 'updated_at']  # ✅ added image
        read_only_fields = ['id', 'created_at', 'updated_at']

    def _abs_url(self, url: str):
        if not url:
            return None
        if url.startswith('http://') or url.startswith('https://'):
            return url
        request = self.context.get('request') if hasattr(self, 'context') else None
        if request:
            try:
                return request.build_absolute_uri(url)
            except Exception:
                pass
        base = getattr(settings, 'MEDIA_URL', '/')
        if base.startswith('http://') or base.startswith('https://'):
            if url.startswith('/'):
                return f"{base.rstrip('/')}{url}"
            return f"{base.rstrip('/')}/{url}"
        return url

    def get_image(self, obj):
        try:
            return self._abs_url(obj.image.url) if obj.image else None
        except Exception:
            return None
