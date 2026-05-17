from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import StaticContent
from .serializers import StaticContentSerializer

class StaticContentViewSet(viewsets.ModelViewSet):
    queryset = StaticContent.objects.all()
    serializer_class = StaticContentSerializer
    lookup_field = 'key'

    def get_permissions(self):
        if self.action in ['retrieve', 'list']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.is_active and not request.user.is_staff:
            return Response({'error': True, 'message': 'Page not active'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
