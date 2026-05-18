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
            'id', 'vehicle_model_id', 'vehicle_model_details',
            'registration_number', 'current_odometer', 'is_default',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        validators = []

    def create(self, validated_data):
        user = validated_data['user']
        vehicle_model = validated_data['vehicle_model']
        instance, created = UserVehicle.objects.get_or_create(
            user=user,
            vehicle_model=vehicle_model,
            defaults={
                'registration_number': validated_data.get('registration_number'),
                'current_odometer': validated_data.get('current_odometer', 0),
                'is_default': validated_data.get('is_default', False),
            },
        )
        if not created:
            update_fields = []
            if 'registration_number' in validated_data:
                instance.registration_number = validated_data['registration_number']
                update_fields.append('registration_number')
            if 'current_odometer' in validated_data:
                instance.current_odometer = validated_data['current_odometer']
                update_fields.append('current_odometer')
            if 'is_default' in validated_data:
                instance.is_default = validated_data['is_default']
                update_fields.append('is_default')
            if update_fields:
                update_fields.append('updated_at')
                instance.save(update_fields=update_fields)
        return instance
