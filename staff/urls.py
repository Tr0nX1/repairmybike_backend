from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ActivityLogViewSet,
    CashReconciliationViewSet,
    CashSessionViewSet,
    PaymentCollectionViewSet,
    StaffBookingViewSet,
    StaffUserViewSet,
)

router = DefaultRouter()
router.register(r'staff', StaffUserViewSet, basename='staff-user')
router.register(r'bookings', StaffBookingViewSet, basename='staff-booking')
router.register(r'logs', ActivityLogViewSet, basename='activity-log')
router.register(r'cash-sessions', CashSessionViewSet, basename='cash-session')
router.register(r'payments', PaymentCollectionViewSet, basename='staff-payment')
router.register(r'reconcile-cash', CashReconciliationViewSet, basename='cash-reconciliation')

urlpatterns = [
    path('', include(router.urls)),
]
