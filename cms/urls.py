from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BannerViewSet
from authentication.views import ContactSubmissionViewSet
from content.views import StaticContentViewSet

router = DefaultRouter()
router.register(r'banners', BannerViewSet, basename='banner')
router.register(r'content', StaticContentViewSet, basename='content')
router.register(r'contact', ContactSubmissionViewSet, basename='contact')

urlpatterns = [
    path('', include(router.urls)),
]

