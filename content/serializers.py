from rest_framework import serializers
from .models import StaticContent

class StaticContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaticContent
        fields = '__all__'
