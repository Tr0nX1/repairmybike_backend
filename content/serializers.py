from rest_framework import serializers
from .models import CarouselItem, SupportOption

class CarouselItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarouselItem
        fields = ['id', 'title', 'subtitle', 'image', 'action_link', 'order']

class SupportOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportOption
        fields = ['id', 'title', 'option_type', 'value', 'icon_image', 'order', 'bg_color']
