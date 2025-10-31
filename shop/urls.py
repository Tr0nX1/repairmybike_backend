from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ShopInfoViewSet

router = DefaultRouter()
router.register(r'shop-info', ShopInfoViewSet, basename='shop-info')

urlpatterns = [
    path('', include(router.urls)),
]