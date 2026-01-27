from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CarouselItemViewSet, SupportOptionViewSet

router = DefaultRouter()
router.register(r'carousel', CarouselItemViewSet)
router.register(r'support', SupportOptionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
