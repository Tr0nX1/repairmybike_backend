from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.cache import cache
from .models import ServiceCategory, Service, ServicePricing, UserSavedService
from .serializers import (
    ServiceCategorySerializer, ServiceSerializer, ServicePricingSerializer,
    UserSavedServiceSerializer
)


class ServiceCategoryViewSet(viewsets.ModelViewSet):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = []  # Temporarily removed for testing
    
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
        
        # Cache for 5 minutes for faster database sync
        cache.set(cache_key, serializer.data, 300)
        
        print(f"✅ Returning fresh data: {len(serializer.data)} categories")
        return Response({
            'error': False,
            'message': 'Service categories retrieved successfully',
            'data': serializer.data
        })


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = []  # Temporarily removed for testing
    
    def get_queryset(self):
        queryset = super().get_queryset()
        category_name = self.request.query_params.get('category', None)
        
        if category_name:
            queryset = queryset.filter(service_category__name=category_name)
            
        return queryset
    
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
        
        # Cache for 5 minutes for faster database sync
        cache.set(cache_key, serializer.data, 300)
        
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
        
        # Cache for 5 minutes instead of 30 minutes
        cache.set(cache_key, serializer.data, 300)
        
        return Response({
            'error': False,
            'message': 'Service pricing retrieved successfully',
            'data': serializer.data
        })


class SavedServiceViewSet(viewsets.ModelViewSet):
    serializer_class = UserSavedServiceSerializer
    
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return UserSavedService.objects.none()
        return UserSavedService.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
             return Response({
                'error': False,
                'data': []
            })
            
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'error': False,
            'message': 'Saved services retrieved',
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {'error': True, 'message': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        updated_data = request.data.copy()
        # 'service_id' is expected in request body
        
        serializer = self.get_serializer(data=updated_data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({
                'error': False,
                'message': 'Service saved successfully',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        return Response({
            'error': True,
            'message': 'Failed to save service',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='remove')
    def remove_service(self, request):
        if not request.user.is_authenticated:
            return Response({'error': True}, status=401)
            
        service_id = request.data.get('service_id')
        deleted, _ = UserSavedService.objects.filter(
            user=request.user, service_id=service_id
        ).delete()
        
        return Response({
            'error': False,
            'message': 'Service removed' if deleted else 'Service not found in saved',
        })