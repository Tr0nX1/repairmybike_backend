from django.urls import path
from .views import (
    RegisterDeviceView, 
    UnregisterDeviceView, 
    NotificationHistoryView,
    WhatsAppHistoryView,
    WhatsAppWebhookView
)

urlpatterns = [
    path('device/', RegisterDeviceView.as_view(), name='register_device'),
    path('device/unregister/', UnregisterDeviceView.as_view(), name='unregister_device'),
    path('history/', NotificationHistoryView.as_view(), name='notification_history'),
    path('whatsapp/history/', WhatsAppHistoryView.as_view(), name='whatsapp_history'),
    path('whatsapp/webhook/', WhatsAppWebhookView.as_view(), name='whatsapp_webhook'),
]
