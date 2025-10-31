from rest_framework import viewsets, status
from rest_framework.response import Response
from django.core.cache import cache
from .models import VehicleType, VehicleBrand, VehicleModel
from .serializers import VehicleTypeSerializer, VehicleBrandSerializer, VehicleModelSerializer


class VehicleTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VehicleType.objects.all()
    serializer_class = VehicleTypeSerializer
    
    def list(self, request, *args, **kwargs):
        cache_key = 'vehicle_types_list'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response({
                'error': False,
                'message': 'Vehicle types retrieved successfully',
                'data': cached_data
            })
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Cache for 1 hour
        cache.set(cache_key, serializer.data, 3600)
        
        return Response({
            'error': False,
            'message': 'Vehicle types retrieved successfully',
            'data': serializer.data
        })


class VehicleBrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VehicleBrand.objects.select_related('vehicle_type').all()
    serializer_class = VehicleBrandSerializer
    filterset_fields = ['vehicle_type']
    
    def list(self, request, *args, **kwargs):
        vehicle_type_id = request.query_params.get('vehicle_type')
        
        if not vehicle_type_id:
            return Response({
                'error': True,
                'message': 'vehicle_type query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        cache_key = f'vehicle_brands_type_{vehicle_type_id}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response({
                'error': False,
                'message': 'Vehicle brands retrieved successfully',
                'data': cached_data
            })
        
        queryset = self.get_queryset().filter(vehicle_type_id=vehicle_type_id)
        serializer = self.get_serializer(queryset, many=True)
        
        # Cache for 1 hour
        cache.set(cache_key, serializer.data, 3600)
        
        return Response({
            'error': False,
            'message': 'Vehicle brands retrieved successfully',
            'data': serializer.data
        })


class VehicleModelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VehicleModel.objects.select_related('vehicle_brand__vehicle_type').all()
    serializer_class = VehicleModelSerializer
    filterset_fields = ['vehicle_brand']
    
    def list(self, request, *args, **kwargs):
        vehicle_brand_id = request.query_params.get('vehicle_brand')
        
        if not vehicle_brand_id:
            return Response({
                'error': True,
                'message': 'vehicle_brand query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        cache_key = f'vehicle_models_brand_{vehicle_brand_id}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response({
                'error': False,
                'message': 'Vehicle models retrieved successfully',
                'data': cached_data
            })
        
        queryset = self.get_queryset().filter(vehicle_brand_id=vehicle_brand_id)
        serializer = self.get_serializer(queryset, many=True)
        
        # Cache for 1 hour
        cache.set(cache_key, serializer.data, 3600)
        
        return Response({
            'error': False,
            'message': 'Vehicle models retrieved successfully',
            'data': serializer.data
        })