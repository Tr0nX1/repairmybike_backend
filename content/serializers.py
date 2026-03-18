from rest_framework import serializers
from .models import CarouselItem, SupportOption, Policy

class CarouselItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarouselItem
        fields = ['id', 'title', 'subtitle', 'image', 'action_link', 'order']

class SupportOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportOption
        fields = ['id', 'title', 'option_type', 'value', 'icon_image', 'order', 'bg_color']

class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = ['id', 'title', 'slug', 'content', 'updated_at']
