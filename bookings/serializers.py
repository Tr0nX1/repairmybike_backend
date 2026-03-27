from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
from .models import Customer, Booking, BookingService, BookingStatusUpdate
from services.models import ServicePricing
from authentication.models import StaffDirectory


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


class StaffDirectorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffDirectory
        fields = ['id', 'name', 'employee_id', 'role', 'skills', 'is_available']


class BookingStatusUpdateSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True, default='')

    class Meta:
        model = BookingStatusUpdate
        fields = ['id', 'status', 'note', 'location_lat', 'location_lng', 'updated_by_name', 'created_at']
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
    address_details = serializers.JSONField(required=False, allow_null=True)
    appointment_date = serializers.DateField()
    appointment_time = serializers.TimeField()
    
    # Payment
    payment_method = serializers.ChoiceField(choices=['cash', 'razorpay'], default='cash')
    notes = serializers.CharField(required=False, allow_blank=True)
    # Optional subscription linkage
    subscription_id = serializers.IntegerField(required=False)
    # Optional coupon
    coupon_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    
    # Optional loyalty points
    use_loyalty_points = serializers.BooleanField(default=False)
    
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
        if data['service_location'] == 'home' and not (data.get('address') or data.get('address_details')):
            raise serializers.ValidationError({"address": "Address or address_details is required for home service"})
        
        # System-wide toggle check for Payment Gateway
        from django.conf import settings
        if not getattr(settings, 'RAZORPAY_ENABLED', False):
            if data.get('payment_method') == 'razorpay':
                raise serializers.ValidationError({
                    "payment_method": "Online payments are currently disabled. Please select Cash on Delivery."
                })
            # Default to cash if not provided or just being safe
            data['payment_method'] = 'cash'

        return data


class BookingListSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    booking_services = BookingServiceSerializer(many=True, read_only=True)
    vehicle_model_name = serializers.CharField(source='vehicle_model.name', read_only=True)
    vehicle_brand_name = serializers.CharField(source='vehicle_model.vehicle_brand.name', read_only=True)
    subscription_remaining_visits = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'customer', 'vehicle_model', 'vehicle_model_name', 'vehicle_brand_name',
            'service_location', 'address', 'address_details', 'appointment_date', 'appointment_time',
            'total_amount', 'payment_method', 'payment_status', 'booking_status',
            'subscription', 'subscription_remaining_visits',
            'notes', 'booking_services', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_subscription_remaining_visits(self, obj):
        try:
            if not obj.subscription:
                return None
            included = obj.subscription.plan.included_visits or 0
            consumed = obj.subscription.visits_consumed or 0
            return max(0, included - consumed)
        except Exception:
            return None


class BookingDetailSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    booking_services = BookingServiceSerializer(many=True, read_only=True)
    vehicle_model_name = serializers.CharField(source='vehicle_model.name', read_only=True)
    vehicle_brand_name = serializers.CharField(source='vehicle_model.vehicle_brand.name', read_only=True)
    vehicle_type_name = serializers.CharField(source='vehicle_model.vehicle_brand.vehicle_type.name', read_only=True)
    subscription_remaining_visits = serializers.SerializerMethodField(read_only=True)
    assigned_staff = StaffDirectorySerializer(read_only=True)
    status_history = BookingStatusUpdateSerializer(many=True, read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'customer', 'vehicle_model', 'vehicle_model_name', 'vehicle_brand_name',
            'vehicle_type_name', 'service_location', 'address', 'address_details', 'appointment_date',
            'appointment_time', 'total_amount', 'payment_method', 'payment_status',
            'booking_status', 'subscription', 'subscription_remaining_visits',
            'assigned_staff', 'status_history',
            'notes', 'booking_services', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


    def get_subscription_remaining_visits(self, obj):
        try:
            if not obj.subscription:
                return None
            included = obj.subscription.plan.included_visits or 0
            consumed = obj.subscription.visits_consumed or 0
            return max(0, included - consumed)
        except Exception:
            return None