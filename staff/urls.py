from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StaffBookingViewSet, StaffOrderViewSet, StaffDashboardViewSet, IssueTicketViewSet

router = DefaultRouter()
router.register(r'bookings', StaffBookingViewSet, basename='staff-booking')
router.register(r'orders', StaffOrderViewSet, basename='staff-order')
router.register(r'dashboard', StaffDashboardViewSet, basename='staff-dashboard')
router.register(r'tickets', IssueTicketViewSet, basename='staff-ticket')

urlpatterns = [
    path('', include(router.urls)),
]