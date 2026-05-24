from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StaticContentViewSet

router = DefaultRouter()
router.register(r'pages', StaticContentViewSet, basename='staticcontent')
router.register(r'static-content', StaticContentViewSet, basename='staticcontent-alias')

urlpatterns = [
    path('', include(router.urls)),
]
