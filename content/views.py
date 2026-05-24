from rest_framework import filters, permissions, status, viewsets
from rest_framework.response import Response
from .models import PolicyContent, StaticContent
from .serializers import PolicyContentSerializer, StaticContentSerializer
from staff.permissions import IsSuperuserOrManager

POLICY_KEY_ALIASES = {
    'terms-and-conditions': ('terms-and-conditions', 'terms'),
    'terms': ('terms', 'terms-and-conditions'),
    'privacy-policy': ('privacy-policy', 'privacy'),
    'privacy': ('privacy', 'privacy-policy'),
    'refund-and-cancellation-policy': (
        'refund-and-cancellation-policy',
        'refund-policy',
        'refund',
    ),
    'refund-policy': (
        'refund-policy',
        'refund-and-cancellation-policy',
        'refund',
    ),
    'shipping-and-delivery-policy': (
        'shipping-and-delivery-policy',
        'shipping-policy',
        'shipping',
    ),
    'shipping-policy': (
        'shipping-policy',
        'shipping-and-delivery-policy',
        'shipping',
    ),
    'payment-policy': ('payment-policy', 'payment'),
    'payment': ('payment', 'payment-policy'),
    'service-policy': ('service-policy', 'service'),
    'service': ('service', 'service-policy'),
}

class StaticContentViewSet(viewsets.ModelViewSet):
    queryset = StaticContent.objects.all()
    serializer_class = StaticContentSerializer
    lookup_field = 'key'
    filter_backends = [filters.SearchFilter]
    search_fields = ['key', 'title']

    def get_permissions(self):
        if self.action in ['retrieve', 'list']:
            return [permissions.AllowAny()]
        return [IsSuperuserOrManager()]

    def _candidate_keys(self, key):
        return POLICY_KEY_ALIASES.get(key, (key,))

    def _get_static_content(self, key):
        queryset = self.filter_queryset(self.get_queryset())

        for candidate in self._candidate_keys(key):
            try:
                return queryset.get(key=candidate)
            except StaticContent.DoesNotExist:
                continue
        return None

    def _get_policy_content(self, key):
        for candidate in self._candidate_keys(key):
            try:
                return PolicyContent.objects.get(slug=candidate)
            except PolicyContent.DoesNotExist:
                continue
        return None

    def get_object(self):
        key = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        obj = self._get_static_content(key) or self._get_policy_content(key)
        if obj is not None:
            self.check_object_permissions(self.request, obj)
            return obj

        self.kwargs[self.lookup_field] = key
        return super().get_object()

    def get_serializer_class(self):
        if isinstance(getattr(self, '_retrieved_instance', None), PolicyContent):
            return PolicyContentSerializer
        return super().get_serializer_class()

    def list(self, request, *args, **kwargs):
        static_queryset = self.filter_queryset(self.get_queryset())
        if static_queryset.exists():
            return super().list(request, *args, **kwargs)

        queryset = PolicyContent.objects.all().order_by('slug')
        if not request.user.is_staff:
            queryset = queryset.filter(is_active=True)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PolicyContentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = PolicyContentSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        self._retrieved_instance = instance
        if not instance.is_active and not request.user.is_staff:
            return Response({'error': True, 'message': 'Page not active'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        key = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        if self._get_static_content(key) is None and self._get_policy_content(key) is not None:
            return Response(
                {'error': True, 'message': 'Legacy policy content is read-only from this endpoint.'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        key = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        if self._get_static_content(key) is None and self._get_policy_content(key) is not None:
            return Response(
                {'error': True, 'message': 'Legacy policy content is read-only from this endpoint.'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        return super().partial_update(request, *args, **kwargs)
