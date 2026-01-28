from rest_framework import serializers
from .models import Review, ReviewPhoto
from django.contrib.contenttypes.models import ContentType

class ReviewPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewPhoto
        fields = ['id', 'image', 'created_at']

class ReviewSerializer(serializers.ModelSerializer):
    photos = ReviewPhotoSerializer(many=True, read_only=True)
    user_name = serializers.ReadOnlyField(source='user.first_name')
    
    class Meta:
        model = Review
        fields = [
            'id', 'user', 'user_name', 'review_type', 'target_id', 
            'rating', 'quality_rating', 'behavior_rating', 'app_rating',
            'comment', 'chips', 'is_verified', 'photos', 'created_at'
        ]
        read_only_fields = ['user', 'is_verified']

    def create(self, validated_data):
        # Logic to extract content_type based on review_type
        review_type = validated_data.get('review_type')
        target_id = self.context['request'].data.get('target_id')
        
        if review_type == 'SERVICE':
            validated_data['content_type'] = ContentType.objects.get(app_label='services', model='service')
        elif review_type == 'PRODUCT':
            validated_data['content_type'] = ContentType.objects.get(app_label='spare_parts', model='sparepart')
            
        validated_data['object_id'] = target_id
        validated_data['user'] = self.context['request'].user
        
        return super().create(validated_data)
