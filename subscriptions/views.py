from django.core.cache import cache
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Plan, Subscription
from .serializers import PlanSerializer, SubscriptionSerializer


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Plan.objects.filter(active=True).order_by("price")
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def list(self, request, *args, **kwargs):
        key = "subscriptions_plans_list"
        cached = cache.get(key)
        if cached:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        cache.set(key, response.data, timeout=60)
        return response


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all().order_by("-created_at")
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ["contact_email", "contact_phone", "plan__name", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        email = self.request.query_params.get("email")
        user_id = self.request.query_params.get("user_id")
        phone = self.request.query_params.get("phone")
        if email:
            qs = qs.filter(contact_email=email)
        if user_id:
            qs = qs.filter(user_id=user_id)
        if phone:
            qs = qs.filter(contact_phone=phone)
        return qs

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