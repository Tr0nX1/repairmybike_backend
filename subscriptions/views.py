from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from staff.permissions import IsSuperuserOrManager
from staff.models import ActivityLog

from .models import Plan, Subscription, PlanBenefit
from .serializers import PlanSerializer, SubscriptionSerializer, PlanBenefitSerializer


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

    @action(detail=True, methods=['post'], url_path='benefits')
    def add_benefit(self, request, pk=None):
        plan = self.get_object()
        text = request.data.get('text', '').strip()
        if not text:
            return Response({'error': 'Benefit text required'}, status=status.HTTP_400_BAD_REQUEST)
        
        benefit = PlanBenefit.objects.create(plan=plan, text=text)
        return Response(PlanBenefitSerializer(benefit).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='benefits/(?P<benefit_id>[^/.]+)')
    def remove_benefit(self, request, pk=None, benefit_id=None):
        plan = self.get_object()
        try:
            benefit = PlanBenefit.objects.get(id=benefit_id, plan=plan)
            benefit.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PlanBenefit.DoesNotExist:
            return Response({'error': 'Benefit not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['patch'], url_path='benefits/(?P<benefit_id>[^/.]+)')
    def update_benefit(self, request, pk=None, benefit_id=None):
        plan = self.get_object()
        try:
            benefit = PlanBenefit.objects.get(id=benefit_id, plan=plan)
        except PlanBenefit.DoesNotExist:
            return Response({'error': 'Benefit not found'}, status=status.HTTP_404_NOT_FOUND)

        text = request.data.get('text')
        is_active = request.data.get('is_active')
        if text is None and is_active is None:
            return Response({'error': 'At least one field is required to update'}, status=status.HTTP_400_BAD_REQUEST)

        if text is not None:
            text = str(text).strip()
            if not text:
                return Response({'error': 'Benefit text cannot be blank'}, status=status.HTTP_400_BAD_REQUEST)
            benefit.text = text
        if is_active is not None:
            if isinstance(is_active, str):
                is_active = is_active.lower() in ['1', 'true', 'yes', 'on']
            benefit.is_active = bool(is_active)
        benefit.save()
        return Response(PlanBenefitSerializer(benefit).data, status=status.HTTP_200_OK)


    def _clear_list_cache(self):
        # Implementation if needed
        pass



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
        
        # If user is authenticated, filter to show their subscriptions by default
        # unless they explicitly filter by different user/phone/email
        if self.request.user and self.request.user.is_authenticated:
            # Check if user is admin/staff - admins can see all
            if not (self.request.user.is_staff or self.request.user.is_superuser):
                # Regular users: show their own subscriptions unless filtering by phone/email
                has_phone_filter = self.request.query_params.get("phone")
                has_email_filter = self.request.query_params.get("email")
                has_user_filter = self.request.query_params.get("user_id")
                
                # Only restrict if no explicit filters are provided
                if not (has_phone_filter or has_email_filter or has_user_filter):
                    qs = qs.filter(user=self.request.user)
        
        # Apply additional filters
        email = self.request.query_params.get("email")
        user_id = self.request.query_params.get("user_id")
        phone = self.request.query_params.get("phone")
        status_param = self.request.query_params.get("status")
        if email:
            qs = qs.filter(contact_email=email)
        if user_id:
            qs = qs.filter(user_id=user_id)
        if phone:
            qs = qs.filter(contact_phone=phone)
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def perform_create(self, serializer):
        """
        Link subscription to authenticated user if available.
        This prevents logout issues when authenticated users create subscriptions.
        """
        # If user is authenticated, link them to the subscription
        if self.request.user and self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Subscription created and linked to user: {self.request.user.id} ({self.request.user.email})")
        else:
            # For guest users, just save without user
            serializer.save()
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Guest subscription created without user link")

    def create(self, request, *args, **kwargs):
        """
        Override create to return consistent response format with authentication preserved.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return success response with consistent format
        return Response({
            'error': False,
            'message': 'Subscription created successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

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
        adjustment = request.data.get('adjustment')
        reason = request.data.get('reason', '').strip()

        if adjustment is None:
            return Response({'error': 'adjustment is required', 'code': 'OUT_OF_BOUNDS'}, status=status.HTTP_400_BAD_REQUEST)
        if not reason:
            return Response({'error': 'reason is required', 'code': 'REASON_REQUIRED'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            adjustment = int(adjustment)
        except (ValueError, TypeError):
            return Response({'error': 'adjustment must be an integer', 'code': 'INVALID_ADJUSTMENT'}, status=status.HTTP_400_BAD_REQUEST)

        included = subscription.plan.included_visits or 0
        old_value = subscription.visits_consumed or 0
        new_value = old_value + adjustment

        if new_value < 0 or new_value > included:
            return Response(
                {
                    'error': f'Visits adjustment out of bounds. Must be between 0 and {included}.',
                    'code': 'OUT_OF_BOUNDS'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription.visits_consumed = new_value
        subscription.save(update_fields=['visits_consumed', 'updated_at'])

        from staff.models import ActivityLog
        ActivityLog.objects.create(
            user=request.user,
            action_type='subscription_visits_adjusted',
            description=f"Adjusted visits for subscription #{subscription.id} by {adjustment}. Reason: {reason}",
            content_object=subscription,
            metadata={
                'subscription_id': str(subscription.id),
                'adjustment': adjustment,
                'old_value': old_value,
                'new_value': new_value,
                'reason': reason,
            }
        )

        return Response({
            'error': False,
            'message': f'Visits adjusted to {new_value}.',
            'data': self.get_serializer(subscription).data
        })

    @action(detail=True, methods=['post'], url_path='approve',
            permission_classes=[permissions.IsAuthenticated, IsSuperuserOrManager])
    def approve(self, request, pk=None):
        subscription = self.get_object()
        
        # Validate current state
        if subscription.status != 'pending':
            return Response(
                {'error': 'Only pending subscriptions can be approved.',
                 'code': 'INVALID_STATUS'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Activate
        now = timezone.now()
        subscription.status = 'active'
        subscription.approved_by = request.user
        subscription.approved_at = now
        
        # Reset visits on fresh activation
        subscription.visits_consumed = 0
        
        # Recompute dates from today
        subscription.start_date = now
        subscription.end_date = None        # clear so save() recomputes
        subscription.next_billing_date = None
        subscription.save()                 # triggers compute_end_date
        
        # Notify customer
        def notify_customer():
            try:
                from notifications.models import Notification
                from repairmybike.fcm import send_push_notification
                plan_name = subscription.plan.name
                visits = subscription.plan.included_visits or 0
                
                Notification.objects.create(
                    user=subscription.user,
                    title="Subscription Activated",
                    message=f"Your {plan_name} plan is now active. "
                            f"You have {visits} visits available.",
                    notification_type='subscription'
                )
                
                if subscription.user:
                    send_push_notification(
                        subscription.user,
                        "Subscription Activated",
                        f"Your {plan_name} plan is now active!",
                        {'type': 'subscription_approved',
                         'subscription_id': str(subscription.id)}
                    )
                
                ActivityLog.objects.create(
                    user=request.user,
                    action_type='subscription_approved',
                    description=f"Approved subscription for {subscription.user.username}",
                    content_object=subscription,
                    metadata={
                        'subscription_id': str(subscription.id),
                        'approved_by': str(request.user.id),
                        'plan': subscription.plan.name,
                        'end_date': str(subscription.end_date),
                    }
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Failed to notify customer of approval: {e}"
                )
        
        transaction.on_commit(notify_customer)
        
        serializer = self.get_serializer(subscription)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='reject',
            permission_classes=[permissions.IsAuthenticated, IsSuperuserOrManager])
    def reject(self, request, pk=None):
        subscription = self.get_object()
        
        if subscription.status != 'pending':
            return Response(
                {'error': 'Only pending subscriptions can be rejected.',
                 'code': 'INVALID_STATUS'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', '')
        
        subscription.status = 'canceled'
        subscription.rejection_reason = reason
        subscription.save()
        
        def notify_customer():
            try:
                from notifications.models import Notification
                from repairmybike.fcm import send_push_notification
                plan_name = subscription.plan.name
                
                Notification.objects.create(
                    user=subscription.user,
                    title="Subscription Request Update",
                    message=f"Your request for {plan_name} could not "
                            f"be approved. Please contact the shop.",
                    notification_type='subscription'
                )
                
                if subscription.user:
                    send_push_notification(
                        subscription.user,
                        "Subscription Request Update",
                        f"Your {plan_name} request was not approved. Please contact the shop.",
                        {'type': 'subscription_rejected',
                         'subscription_id': str(subscription.id)}
                    )
                
                ActivityLog.objects.create(
                    user=request.user,
                    action_type='subscription_rejected',
                    description=f"Rejected subscription for {subscription.user.username}",
                    content_object=subscription,
                    metadata={
                        'subscription_id': str(subscription.id),
                        'rejected_by': str(request.user.id),
                        'reason': reason,
                    }
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Failed to notify customer of rejection: {e}"
                )
        
        transaction.on_commit(notify_customer)
        
        serializer = self.get_serializer(subscription)
        return Response(serializer.data)