from rest_framework import serializers
from shop.models import ShopInfo
from .models import QuickServiceConfig, QuickServiceRequest


class QuickServiceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickServiceConfig
        fields = ['id', 'title', 'rules_html', 'base_price', 'support_phone']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Fallback to ShopInfo active phone if support_phone is blank
        if not ret.get('support_phone'):
            active_shop = ShopInfo.objects.filter(is_active=True).order_by('-id').first()
            if active_shop and active_shop.phone:
                ret['support_phone'] = active_shop.phone
        return ret


class QuickServiceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickServiceRequest
        fields = [
            'id',
            'name',
            'phone_number',
            'vehicle_number',
            'vehicle_manufacturer',
            'vehicle_model',
            'status',
            'staff_notes',
            'services_grabbed',
            'total_amount',
            'guest_id',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class QuickServiceRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickServiceRequest
        fields = [
            'id',
            'name',
            'phone_number',
            'vehicle_number',
            'vehicle_manufacturer',
            'vehicle_model',
            'status',
            'staff_notes',
            'services_grabbed',
            'total_amount',
            'guest_id',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'staff_notes',
            'services_grabbed',
            'total_amount',
            'guest_id',
            'created_at',
            'updated_at',
        ]
        extra_kwargs = {
            'name': {'required': True, 'allow_blank': False},
            'phone_number': {'required': True, 'allow_blank': False},
        }


class QuickServiceRequestStaffUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickServiceRequest
        fields = [
            'id',
            'name',
            'phone_number',
            'vehicle_number',
            'vehicle_manufacturer',
            'vehicle_model',
            'status',
            'staff_notes',
            'services_grabbed',
            'total_amount',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'name', 'phone_number', 'created_at', 'updated_at']

    def validate_status(self, value):
        valid_statuses = [choice[0] for choice in QuickServiceRequest.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status '{value}'. Valid statuses: {valid_statuses}")
        return value
