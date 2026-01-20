from rest_framework import serializers
from django.conf import settings
from .models import VehicleType, VehicleBrand, VehicleModel, UserVehicle


class VehicleTypeSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = VehicleType
        fields = ['id', 'name', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_image(self, obj):
        """Returns absolute URL from storage backend"""
        try:
            return obj.image.url if obj.image else None
        except Exception:
            return None


class VehicleBrandSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    vehicle_type_name = serializers.CharField(source='vehicle_type.name', read_only=True)
    
    class Meta:
        model = VehicleBrand
        fields = ['id', 'vehicle_type', 'vehicle_type_name', 'name', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_image(self, obj):
        """Returns absolute URL from storage backend"""
        try:
            return obj.image.url if obj.image else None
        except Exception:
            return None


class VehicleModelSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    brand_name = serializers.CharField(source='vehicle_brand.name', read_only=True)
    vehicle_type_name = serializers.CharField(source='vehicle_brand.vehicle_type.name', read_only=True)
    
    class Meta:
        model = VehicleModel
        fields = ['id', 'vehicle_brand', 'brand_name', 'vehicle_type_name', 'name', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_image(self, obj):
        """Returns absolute URL from storage backend"""
        try:
            return obj.image.url if obj.image else None
        except Exception:
            return None


class UserVehicleSerializer(serializers.ModelSerializer):
    vehicle_model_details = VehicleModelSerializer(source='vehicle_model', read_only=True)
    vehicle_model_id = serializers.PrimaryKeyRelatedField(
        queryset=VehicleModel.objects.all(), source='vehicle_model', write_only=True
    )
    
    class Meta:
        model = UserVehicle
        fields = ['id', 'vehicle_model_id', 'vehicle_model_details', 'registration_number', 'is_default', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
