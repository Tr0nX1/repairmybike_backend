from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import models
from django.utils import timezone
from .models import Banner
from .serializers import BannerSerializer

class BannerViewSet(viewsets.ModelViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = Banner.objects.filter(is_active=True)
        if not self.request.user.is_staff:
            now = timezone.now().date()
            qs = qs.filter(
                models.Q(start_date__isnull=True) | models.Q(start_date__lte=now),
                models.Q(end_date__isnull=True) | models.Q(end_date__gte=now)
            )
        return qs.order_by('display_order', '-created_at')

    def get_permissions(self):
        if self.action == 'list':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def perform_create(self, serializer):
        image = self.request.FILES.get('image')
        if image:
            serializer.save(image=image)
        else:
            serializer.save()

    def perform_update(self, serializer):
        image = self.request.FILES.get('image')
        if image:
            serializer.save(image=image)
        else:
            serializer.save()
