from rest_framework import viewsets, status
from rest_framework.response import Response
from django.core.cache import cache
from .models import ShopInfo
from .serializers import ShopInfoSerializer


class ShopInfoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ShopInfo.objects.filter(is_active=True)
    serializer_class = ShopInfoSerializer
    
    def list(self, request, *args, **kwargs):
        """
        Get shop information
        """
        cache_key = 'shop_info_list'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response({
                'error': False,
                'message': 'Shop information retrieved successfully',
                'data': cached_data
            })
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Cache for 1 hour
        cache.set(cache_key, serializer.data, 3600)
        
        return Response({
            'error': False,
            'message': 'Shop information retrieved successfully',
            'data': serializer.data
        })
    
    def retrieve(self, request, *args, **kwargs):
        """
        Get single shop details
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'error': False,
            'message': 'Shop details retrieved successfully',
            'data': serializer.data
        })