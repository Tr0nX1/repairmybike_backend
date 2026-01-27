from rest_framework import serializers
from .models import QuickServiceConfig, QuickServiceRequest

class QuickServiceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickServiceConfig
        fields = ['id', 'title', 'rules_html', 'base_price', 'support_phone']

class QuickServiceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickServiceRequest
        fields = ['id', 'user', 'phone_number', 'status', 'staff_notes', 'services_grabbed', 'total_amount', 'created_at', 'updated_at']
        read_only_fields = ['user', 'status', 'staff_notes', 'services_grabbed', 'total_amount']
