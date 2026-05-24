from django.core.cache import cache
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response

from staff.permissions import IsSuperuserOrManager

from .models import ShopInfo
from .serializers import ShopInfoSerializer


class ShopInfoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ShopInfoSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update']:
            return [IsSuperuserOrManager()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        user = getattr(self.request, 'user', None)
        if user and user.is_authenticated and (user.is_superuser or getattr(user, 'is_manager', False)):
            return ShopInfo.objects.all().order_by('-id')
        return ShopInfo.objects.filter(is_active=True).order_by('-id')

    def list(self, request, *args, **kwargs):
        cache_key = 'shop_info_list'
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response({
                'error': False,
                'message': 'Shop information retrieved successfully',
                'data': cached_data,
            })

        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        cache.set(cache_key, serializer.data, 3600)

        return Response({
            'error': False,
            'message': 'Shop information retrieved successfully',
            'data': serializer.data,
        })

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response({
            'error': False,
            'message': 'Shop details retrieved successfully',
            'data': serializer.data,
        })

    def update(self, request, *args, **kwargs):
        return self._update_instance(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self._update_instance(request, *args, **kwargs)

    def _update_instance(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'error': False,
            'message': 'Shop information updated successfully',
            'data': serializer.data,
        }, status=status.HTTP_200_OK)

    def perform_update(self, serializer):
        serializer.save()
        cache.delete('shop_info_list')