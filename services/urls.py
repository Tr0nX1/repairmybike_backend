from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceCategoryViewSet, ServiceViewSet, ServicePricingViewSet, SavedServiceViewSet

router = DefaultRouter()
router.register(r'service-categories', ServiceCategoryViewSet, basename='service-category')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'service-pricing', ServicePricingViewSet, basename='service-pricing')
router.register(r'saved-services', SavedServiceViewSet, basename='b-saved-services')

urlpatterns = [
    path('', include(router.urls)),
]