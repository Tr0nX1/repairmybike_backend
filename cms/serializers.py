from rest_framework import serializers
from .models import Banner

class BannerSerializer(serializers.ModelSerializer):
    final_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = '__all__'

    def get_final_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return obj.image_url
