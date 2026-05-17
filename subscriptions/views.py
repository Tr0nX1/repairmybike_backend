from django.core.cache import cache
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Plan, Subscription, PlanBenefit

from .serializers import PlanSerializer, SubscriptionSerializer


class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.filter(active=True).order_by("price")
    serializer_class = PlanSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def perform_create(self, serializer):
        image = self.request.FILES.get('image')
        if image:
            serializer.save(image=image)
        else:
            serializer.save()
        self._clear_list_cache()

    def perform_update(self, serializer):
        image = self.request.FILES.get('image')
        if image:
            serializer.save(image=image)
        else:
            serializer.save()
        self._clear_list_cache()



class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all().order_by("-created_at")
    serializer_class = SubscriptionSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["contact_email", "contact_phone", "plan__name", "status"]

    def get_permissions(self):
        if self.action in ['adjust_visits', 'cancel', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.AllowAny()]

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

    @action(detail=True, methods=['post'], url_path='adjust-visits')
    def adjust_visits(self, request, pk=None):
        subscription = self.get_object()
        visits_to_add = request.data.get('visits_to_add')
        reason = request.data.get('reason', '')

        if visits_to_add is None:
            return Response({'error': 'visits_to_add is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            visits_to_add = int(visits_to_add)
        except ValueError:
            return Response({'error': 'visits_to_add must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

        subscription.visits_remaining += visits_to_add
        subscription.save()

        from staff.models import ActivityLog
        ActivityLog.objects.create(
            user=request.user,
            action_type='subscription_adjustment',
            description=f"Adjusted visits for subscription #{subscription.id} by {visits_to_add}. Reason: {reason}",
            content_object=subscription,
            metadata={'adjustment': visits_to_add, 'reason': reason}
        )

        return Response({
            'error': False,
            'message': f"Added {visits_to_add} visits. Total remaining: {subscription.visits_remaining}",
            'data': self.get_serializer(subscription).data
        })