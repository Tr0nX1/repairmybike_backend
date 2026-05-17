from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet

router = DefaultRouter()
# Register at root level so /api/bookings/ works directly (for Flutter)
# Also keep the nested path for backward compatibility
router.register(r'', BookingViewSet, basename='booking')
router.register(r'bookings', BookingViewSet, basename='booking-nested')

urlpatterns = [
    path('', include(router.urls)),
]