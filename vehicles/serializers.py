from rest_framework import serializers
from .models import VehicleType, VehicleBrand, VehicleModel


class VehicleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleType
        fields = ['id', 'name', 'image', 'created_at', 'updated_at']  # ✅ added image
        read_only_fields = ['id', 'created_at', 'updated_at']


class VehicleBrandSerializer(serializers.ModelSerializer):
    vehicle_type_name = serializers.CharField(source='vehicle_type.name', read_only=True)
    
    class Meta:
        model = VehicleBrand
        fields = ['id', 'vehicle_type', 'vehicle_type_name', 'name', 'image', 'created_at', 'updated_at']  # ✅ added image
        read_only_fields = ['id', 'created_at', 'updated_at']


class VehicleModelSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source='vehicle_brand.name', read_only=True)
    vehicle_type_name = serializers.CharField(source='vehicle_brand.vehicle_type.name', read_only=True)
    
    class Meta:
        model = VehicleModel
        fields = ['id', 'vehicle_brand', 'brand_name', 'vehicle_type_name', 'name', 'image', 'created_at', 'updated_at']  # ✅ added image
        read_only_fields = ['id', 'created_at', 'updated_at']
