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
        """Returns standardized media object"""
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


class VehicleBrandSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    vehicle_type_name = serializers.CharField(source='vehicle_type.name', read_only=True)
    
    class Meta:
        model = VehicleBrand
        fields = ['id', 'vehicle_type', 'vehicle_type_name', 'name', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_image(self, obj):
        """Returns standardized media object"""
        if not obj.image:
            return None
        try:
            url = obj.image.url
            return {
                "thumbnail": url,
                "original": url,
                "alt_text": f"{obj.name} - {obj.vehicle_type.name}"
            }
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
        """Returns standardized media object"""
        if not obj.image:
            return None
        try:
            url = obj.image.url
            return {
                "thumbnail": url,
                "original": url,
                "alt_text": f"{obj.name} - {obj.vehicle_brand.name}"
            }
        except Exception:
            return None


class UserVehicleSerializer(serializers.ModelSerializer):
    vehicle_model_details = VehicleModelSerializer(source='vehicle_model', read_only=True)
    vehicle_model_id = serializers.PrimaryKeyRelatedField(
        queryset=VehicleModel.objects.all(), source='vehicle_model', write_only=True
    )
    
    class Meta:
        model = UserVehicle
        fields = [
            'id', 'vehicle_model_id', 'vehicle_model_details', 'registration_number', 
            'is_default', 'last_service_date', 'current_odometer', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VehicleHistorySerializer(serializers.Serializer):
    """Simple serializer for booking history entries."""
    id = serializers.IntegerField()
    appointment_date = serializers.DateField()
    booking_status = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    odometer_reading = serializers.IntegerField()
    service_names = serializers.SerializerMethodField()

    def get_service_names(self, obj):
        return [bs.service.name for bs in obj.booking_services.all()]
