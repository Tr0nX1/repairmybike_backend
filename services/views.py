from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.core.cache import cache
from .models import ServiceCategory, Service, ServicePricing, UserSavedService, GuestSavedService
from .serializers import (
    ServiceCategorySerializer, ServiceSerializer, ServicePricingSerializer,
    UserSavedServiceSerializer, GuestSavedServiceSerializer
)
from authentication.permissions import IsGuestOrAuthenticated
from authentication.models import GuestSession


class ServiceCategoryViewSet(viewsets.ModelViewSet):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        image = self.request.FILES.get('image')
        if image:
            serializer.save(image=image)
        else:
            serializer.save()
        cache.delete('service_categories_list')

    def perform_update(self, serializer):
        image = self.request.FILES.get('image')
        if image:
            serializer.save(image=image)
        else:
            serializer.save()
        cache.delete('service_categories_list')

    
    def list(self, request, *args, **kwargs):
        cache_key = 'service_categories_list'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response({
                'error': False,
                'message': 'Service categories retrieved successfully',
                'data': cached_data
            })
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Cache for 5 minutes
        cache.set(cache_key, serializer.data, 300)
        
        return Response({
            'error': False,
            'message': 'Service categories retrieved successfully',
            'data': serializer.data
        })


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        images = self.request.FILES.get('images')
        if images:
            serializer.save(images=images)
        else:
            serializer.save()
        cache.delete('services_all')

    def perform_update(self, serializer):
        images = self.request.FILES.get('images')
        if images:
            serializer.save(images=images)
        else:
            serializer.save()
        cache.delete('services_all')

    
    def get_queryset(self):
        queryset = super().get_queryset()
        category_name = self.request.query_params.get('category', None)
        
        if category_name:
            queryset = queryset.filter(service_category__name=category_name)
            
        return queryset
    
    def list(self, request, *args, **kwargs):
        category_id = request.query_params.get('category_id')
        user = request.user
        user_identifier = f"user_{user.id}" if user.is_authenticated else (f"guest_{user.guest_id}" if getattr(user, 'is_guest', False) else "anon")
        
        if category_id:
            cache_key = f'services_category_{category_id}_{user_identifier}'
            queryset = self.get_queryset().filter(service_category_id=category_id)
        else:
            cache_key = f'services_all_{user_identifier}'
            queryset = self.get_queryset()

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response({
                'error': False,
                'message': 'Services retrieved successfully',
                'data': cached_data
            })
        
        serializer = self.get_serializer(queryset, many=True)
        
        # Cache for 5 minutes
        cache.set(cache_key, serializer.data, 300)
        
        return Response({
            'error': False,
            'message': 'Services retrieved successfully',
            'data': serializer.data
        })


class ServicePricingViewSet(viewsets.ModelViewSet):
    queryset = ServicePricing.objects.select_related(
        'service__service_category',
        'vehicle_model'
    ).all()
    serializer_class = ServicePricingSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]
    
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
        
        # Cache for 5 minutes
        cache.set(cache_key, serializer.data, 300)
        
        return Response({
            'error': False,
            'message': 'Service pricing retrieved successfully',
            'data': serializer.data
        })


class SavedServiceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsGuestOrAuthenticated]

    def get_serializer_class(self):
        if self.request.user.is_authenticated:
            return UserSavedServiceSerializer
        return GuestSavedServiceSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return UserSavedService.objects.filter(user=user)
        
        # Guest User logic
        guest_id = getattr(user, 'guest_id', None)
        if guest_id:
            return GuestSavedService.objects.filter(guest_session__guest_id=guest_id)
            
        return GuestSavedService.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'error': False,
            'message': 'Saved services retrieved',
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        user = request.user
        service_id = request.data.get('service_id')
        
        if not service_id:
             return Response({'error': True, 'message': 'service_id is required'}, status=400)

        if user.is_authenticated:
            saved_obj, created = UserSavedService.objects.get_or_create(
                user=user, service_id=service_id
            )
            serializer = UserSavedServiceSerializer(saved_obj)
        else:
            # Guest Logic
            guest_id = getattr(user, 'guest_id', None)
            guest_session = GuestSession.objects.filter(guest_id=guest_id).first()
            if not guest_session:
                 return Response({'error': True, 'message': 'Invalid guest session'}, status=401)
            
            saved_obj, created = GuestSavedService.objects.get_or_create(
                guest_session=guest_session, service_id=service_id
            )
            serializer = GuestSavedServiceSerializer(saved_obj)

        return Response({
            'error': False,
            'message': 'Service saved successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='remove')
    def remove_service(self, request):
        user = request.user
        service_id = request.data.get('service_id')
        
        if user.is_authenticated:
            deleted, _ = UserSavedService.objects.filter(
                user=user, service_id=service_id
            ).delete()
        else:
            guest_id = getattr(user, 'guest_id', None)
            deleted, _ = GuestSavedService.objects.filter(
                guest_session__guest_id=guest_id, service_id=service_id
            ).delete()
        
        return Response({
            'error': False,
            'message': 'Service removed' if deleted else 'Service not found in saved',
        })