from rest_framework import serializers
from .models import NotificationLog, WhatsAppMessage

class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = ['id', 'title', 'body', 'data', 'sent_at']

class WhatsAppMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppMessage
        fields = ['id', 'phone_number', 'message_text', 'status', 'kapso_message_id', 'sent_at']
