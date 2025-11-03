from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    SparePartCategoryViewSet,
    SparePartBrandViewSet,
    SparePartViewSet,
    CartViewSet,
)

router = DefaultRouter()
router.register(r'categories', SparePartCategoryViewSet, basename='spare-part-category')
router.register(r'brands', SparePartBrandViewSet, basename='spare-part-brand')
router.register(r'parts', SparePartViewSet, basename='spare-part')
router.register(r'cart', CartViewSet, basename='spare-part-cart')

urlpatterns = [
    path('', include(router.urls)),
]