from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceCategoryViewSet, ServiceViewSet, ServicePricingViewSet

router = DefaultRouter()
router.register(r'service-categories', ServiceCategoryViewSet, basename='service-category')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'service-pricing', ServicePricingViewSet, basename='service-pricing')

urlpatterns = [
    path('', include(router.urls)),
]