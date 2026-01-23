from django.core.cache import cache
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Plan, Subscription
from .serializers import PlanSerializer, SubscriptionSerializer


class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.filter(active=True).order_by("price")
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def _clear_list_cache(self):
        cache.delete("subscriptions_plans_list")

    def list(self, request, *args, **kwargs):
        key = "subscriptions_plans_list"
        cached = cache.get(key)
        if cached:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set(key, response.data, timeout=60)
        return response

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        self._clear_list_cache()
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        self._clear_list_cache()
        return response

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        self._clear_list_cache()
        return response

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        self._clear_list_cache()
        return response


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all().order_by("-created_at")
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["contact_email", "contact_phone", "plan__name", "status"]

    def get_queryset(self):
        # Users can see subscriptions linked to their account OR their phone number
        user = self.request.user
        qs = Subscription.objects.all().order_by("-created_at")
        
        if user.is_authenticated:
            # Match strictly by User ID (Session) as requested
            return qs.filter(user=user)
            
        return qs.none() # Should not happen due to permission_classes

    def perform_create(self, serializer):
        # Automatically link to authenticated user
        user = self.request.user
        serializer.save(
            user=user if user.is_authenticated else None,
            contact_email=serializer.validated_data.get('contact_email') or getattr(user, 'email', None),
            contact_phone=serializer.validated_data.get('contact_phone') or getattr(user, 'phone_number', None)
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return Response({
                'error': False,
                'message': 'Subscriptions retrieved successfully',
                'data': serializer.data,
            })
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'error': False,
            'message': 'Subscriptions retrieved successfully',
            'data': serializer.data,
        })

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        sub = self.get_object()
        sub.status = "canceled"
        sub.auto_renew = False
        sub.save(update_fields=["status", "auto_renew", "updated_at"])
        return Response({"status": "canceled"}, status=status.HTTP_200_OK)