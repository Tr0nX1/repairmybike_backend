from rest_framework import serializers
from .models import ServiceCategory, Service, ServicePricing


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