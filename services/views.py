from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.cache import cache
from .models import ServiceCategory, Service, ServicePricing
from .serializers import ServiceCategorySerializer, ServiceSerializer, ServicePricingSerializer


class ServiceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    
    def list(self, request, *args, **kwargs):
        print("🔍 ServiceCategoryViewSet.list() called")
        print(f"📊 Request method: {request.method}")
        print(f"🌐 Request headers: {dict(request.headers)}")
        
        cache_key = 'service_categories_list'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            print(f"✅ Returning cached data: {len(cached_data)} categories")
            return Response({
                'error': False,
                'message': 'Service categories retrieved successfully',
                'data': cached_data
            })
        
        queryset = self.get_queryset()
        print(f"📋 Queryset count: {queryset.count()}")
        
        serializer = self.get_serializer(queryset, many=True)
        print(f"📝 Serialized data: {serializer.data}")
        
        # Cache for 1 hour
        cache.set(cache_key, serializer.data, 3600)
        
        print(f"✅ Returning fresh data: {len(serializer.data)} categories")
        return Response({
            'error': False,
            'message': 'Service categories retrieved successfully',
            'data': serializer.data
        })


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Service.objects.select_related('service_category').all()
    serializer_class = ServiceSerializer
    filterset_fields = ['service_category']
    
    def list(self, request, *args, **kwargs):
        print("🔍 ServiceViewSet.list() called")
        print(f"📊 Request method: {request.method}")
        print(f"🌐 Request headers: {dict(request.headers)}")
        
        category_id = request.query_params.get('category_id')
        print(f"🏷️ Category ID filter: {category_id}")
        
        if category_id:
            cache_key = f'services_category_{category_id}'
            cached_data = cache.get(cache_key)
            
            if cached_data:
                print(f"✅ Returning cached data for category {category_id}: {len(cached_data)} services")
                return Response({
                    'error': False,
                    'message': 'Services retrieved successfully',
                    'data': cached_data
                })
            
            queryset = self.get_queryset().filter(service_category_id=category_id)
            print(f"📋 Filtered queryset count: {queryset.count()}")
        else:
            cache_key = 'services_all'
            cached_data = cache.get(cache_key)
            
            if cached_data:
                print(f"✅ Returning cached data for all services: {len(cached_data)} services")
                return Response({
                    'error': False,
                    'message': 'Services retrieved successfully',
                    'data': cached_data
                })
            
            queryset = self.get_queryset()
            print(f"📋 All services queryset count: {queryset.count()}")
        
        serializer = self.get_serializer(queryset, many=True)
        print(f"📝 Serialized data: {serializer.data}")
        
        # Cache for 1 hour
        cache.set(cache_key, serializer.data, 3600)
        
        print(f"✅ Returning fresh data: {len(serializer.data)} services")
        return Response({
            'error': False,
            'message': 'Services retrieved successfully',
            'data': serializer.data
        })


class ServicePricingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServicePricing.objects.select_related(
        'service__service_category',
        'vehicle_model'
    ).all()
    serializer_class = ServicePricingSerializer
    
    @action(detail=False, methods=['get'], url_path='by-vehicle')
    def by_vehicle(self, request):
        vehicle_model_id = request.query_params.get('vehicle_model_id')
        
        if not vehicle_model_id:
            return Response({
                'error': True,
                'message': 'vehicle_model_id query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        cache_key = f'service_pricing_vehicle_{vehicle_model_id}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response({
                'error': False,
                'message': 'Service pricing retrieved successfully',
                'data': cached_data
            })
        
        queryset = self.get_queryset().filter(vehicle_model_id=vehicle_model_id)
        serializer = self.get_serializer(queryset, many=True)
        
        # Cache for 30 minutes
        cache.set(cache_key, serializer.data, 1800)
        
        return Response({
            'error': False,
            'message': 'Service pricing retrieved successfully',
            'data': serializer.data
        })