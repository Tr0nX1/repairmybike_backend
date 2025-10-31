from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
from .models import Customer, Booking, BookingService
from services.models import ServicePricing


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'phone', 'email', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class BookingServiceSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    category_name = serializers.CharField(source='service.service_category.name', read_only=True)
    
    class Meta:
        model = BookingService
        fields = ['id', 'service', 'service_name', 'category_name', 'price', 'created_at']
        read_only_fields = ['id', 'created_at']


class BookingCreateSerializer(serializers.Serializer):
    # Customer Info
    customer_name = serializers.CharField(max_length=100)
    customer_phone = serializers.CharField(max_length=17)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    
    # Vehicle Info
    vehicle_model_id = serializers.IntegerField()
    
    # Service Info
    service_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    
    # Booking Details
    service_location = serializers.ChoiceField(choices=['home', 'shop'])
    address = serializers.CharField(required=False, allow_blank=True)
    appointment_date = serializers.DateField()
    appointment_time = serializers.TimeField()
    
    # Payment
    payment_method = serializers.ChoiceField(choices=['cash', 'razorpay'], default='cash')
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_customer_phone(self, value):
        # Basic phone validation
        import re
        if not re.match(r'^\+?1?\d{9,15}$', value):
            raise serializers.ValidationError("Invalid phone number format")
        return value
    
    def validate_appointment_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Appointment date cannot be in the past")
        return value
    
    def validate(self, data):
        # Validate address for home service
        if data['service_location'] == 'home' and not data.get('address'):
            raise serializers.ValidationError({"address": "Address is required for home service"})
        
        return data


class BookingListSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    booking_services = BookingServiceSerializer(many=True, read_only=True)
    vehicle_model_name = serializers.CharField(source='vehicle_model.name', read_only=True)
    vehicle_brand_name = serializers.CharField(source='vehicle_model.vehicle_brand.name', read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'customer', 'vehicle_model', 'vehicle_model_name', 'vehicle_brand_name',
            'service_location', 'address', 'appointment_date', 'appointment_time',
            'total_amount', 'payment_method', 'payment_status', 'booking_status',
            'notes', 'booking_services', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BookingDetailSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    booking_services = BookingServiceSerializer(many=True, read_only=True)
    vehicle_model_name = serializers.CharField(source='vehicle_model.name', read_only=True)
    vehicle_brand_name = serializers.CharField(source='vehicle_model.vehicle_brand.name', read_only=True)
    vehicle_type_name = serializers.CharField(source='vehicle_model.vehicle_brand.vehicle_type.name', read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'customer', 'vehicle_model', 'vehicle_model_name', 'vehicle_brand_name',
            'vehicle_type_name', 'service_location', 'address', 'appointment_date',
            'appointment_time', 'total_amount', 'payment_method', 'payment_status',
            'booking_status', 'notes', 'booking_services', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']