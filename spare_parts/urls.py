from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    SparePartCategoryViewSet,
    SparePartBrandViewSet,
    SparePartViewSet,
    CartViewSet,
    OrderViewSet,
)

router = DefaultRouter()
router.register(r'categories', SparePartCategoryViewSet, basename='spare-part-category')
router.register(r'brands', SparePartBrandViewSet, basename='spare-part-brand')
router.register(r'parts', SparePartViewSet, basename='spare-part')
router.register(r'cart', CartViewSet, basename='spare-part-cart')
router.register(r'orders', OrderViewSet, basename='spare-part-order')

urlpatterns = [
    path('', include(router.urls)),
]
