from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VehicleTypeViewSet, VehicleBrandViewSet, VehicleModelViewSet

router = DefaultRouter()
router.register(r'vehicle-types', VehicleTypeViewSet, basename='vehicle-type')
router.register(r'vehicle-brands', VehicleBrandViewSet, basename='vehicle-brand')
router.register(r'vehicle-models', VehicleModelViewSet, basename='vehicle-model')

urlpatterns = [
    path('', include(router.urls)),
]