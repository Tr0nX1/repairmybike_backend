from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import QuickServiceConfig, QuickServiceRequest
from .serializers import QuickServiceConfigSerializer, QuickServiceRequestSerializer

class QuickServiceConfigViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows quick service config to be viewed.
    """
    queryset = QuickServiceConfig.objects.filter(is_active=True)
    serializer_class = QuickServiceConfigSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

class QuickServiceRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint for users to create and view their quick service requests.
    """
    serializer_class = QuickServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return QuickServiceRequest.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
