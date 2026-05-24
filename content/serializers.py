from rest_framework import serializers
from .models import PolicyContent, StaticContent


class StaticContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaticContent
        fields = (
            'id',
            'key',
            'title',
            'body',
            'is_active',
            'updated_at',
        )
        read_only_fields = ('id', 'updated_at')


class PolicyContentSerializer(serializers.ModelSerializer):
    key = serializers.CharField(source='slug', read_only=True)
    body = serializers.CharField(source='content', read_only=True)

    class Meta:
        model = PolicyContent
        fields = (
            'id',
            'key',
            'slug',
            'title',
            'body',
            'content',
            'is_active',
            'updated_at',
        )
