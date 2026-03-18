from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CarouselItemViewSet, SupportOptionViewSet, PolicyViewSet

router = DefaultRouter()
router.register(r'carousel', CarouselItemViewSet)
router.register(r'support', SupportOptionViewSet)
router.register(r'policy', PolicyViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
