from django.urls import path
from .views import RegisterDeviceView, UnregisterDeviceView

urlpatterns = [
    path('device/', RegisterDeviceView.as_view(), name='register_device'),
    path('device/unregister/', UnregisterDeviceView.as_view(), name='unregister_device'),
]
