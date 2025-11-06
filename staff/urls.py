from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StaffBookingViewSet

router = DefaultRouter()
router.register(r'bookings', StaffBookingViewSet, basename='staff-booking')

urlpatterns = [
    path('', include(router.urls)),
]