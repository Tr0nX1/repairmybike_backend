from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuickServiceConfigViewSet, QuickServiceRequestViewSet

router = DefaultRouter()
router.register(r'config', QuickServiceConfigViewSet)
router.register(r'requests', QuickServiceRequestViewSet, basename='quickservicerequest')

urlpatterns = [
    path('', include(router.urls)),
]
