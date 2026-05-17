from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.core.cache import cache
from .models import VehicleType, VehicleBrand, VehicleModel, UserVehicle
from .serializers import (
    VehicleTypeSerializer, 
    VehicleBrandSerializer, 
    VehicleModelSerializer,
    UserVehicleSerializer
)


class VehicleTypeViewSet(viewsets.ModelViewSet):
    queryset = VehicleType.objects.all().order_by('name')
    serializer_class = VehicleTypeSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save()
        cache.delete('vehicle_types_list')

    def perform_update(self, serializer):
        serializer.save()
        cache.delete('vehicle_types_list')

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete('vehicle_types_list')


class VehicleBrandViewSet(viewsets.ModelViewSet):
    queryset = VehicleBrand.objects.select_related('vehicle_type').all().order_by('name')
    serializer_class = VehicleBrandSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ['vehicle_type']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        brand = serializer.save()
        cache.delete(f'vehicle_brands_type_{brand.vehicle_type_id}')

    def perform_update(self, serializer):
        brand = serializer.save()
        cache.delete(f'vehicle_brands_type_{brand.vehicle_type_id}')


class VehicleModelViewSet(viewsets.ModelViewSet):
    queryset = VehicleModel.objects.select_related('vehicle_brand__vehicle_type').all().order_by('name')
    serializer_class = VehicleModelSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ['vehicle_brand']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        model = serializer.save()
        cache.delete(f'vehicle_models_brand_{model.vehicle_brand_id}')

    def perform_update(self, serializer):
        model = serializer.save()
        cache.delete(f'vehicle_models_brand_{model.vehicle_brand_id}')


class UserVehicleViewSet(viewsets.ModelViewSet):
    serializer_class = UserVehicleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserVehicle.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Handle setting is_default logic if needed
        if serializer.validated_data.get('is_default', False):
            UserVehicle.objects.filter(user=self.request.user, is_default=True).update(is_default=False)
        serializer.save(user=self.request.user)