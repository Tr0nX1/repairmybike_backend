from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, RefundViewSet

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'refunds', RefundViewSet, basename='refund')

urlpatterns = [
    path('', include(router.urls)),
]