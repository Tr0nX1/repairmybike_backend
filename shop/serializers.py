from rest_framework import serializers
from .models import ShopInfo


class ShopInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopInfo
        fields = [
            'id', 'name', 'address', 'phone', 'email',
            'latitude', 'longitude', 'opening_time', 'closing_time',
            'working_days', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']