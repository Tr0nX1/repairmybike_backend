from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StaticContentViewSet

router = DefaultRouter()
router.register(r'pages', StaticContentViewSet, basename='staticcontent')

urlpatterns = [
    path('', include(router.urls)),
]
