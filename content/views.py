from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import CarouselItem, SupportOption
from .serializers import CarouselItemSerializer, SupportOptionSerializer

class CarouselItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows active carousel items to be viewed.
    """
    queryset = CarouselItem.objects.filter(is_active=True)
    serializer_class = CarouselItemSerializer
    permission_classes = [AllowAny]
    pagination_class = None  # No pagination needed for carousel

class SupportOptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows active support options to be viewed.
    """
    queryset = SupportOption.objects.filter(is_active=True)
    serializer_class = SupportOptionSerializer
    permission_classes = [AllowAny]
    pagination_class = None
