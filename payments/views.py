from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
import razorpay
import hmac
import hashlib
from .models import Payment, Refund
from .serializers import (
    PaymentSerializer,
    RazorpayOrderCreateSerializer,
    RazorpayPaymentVerifySerializer,
    RefundSerializer,
    RefundRequestSerializer,
    RefundProcessSerializer,
)
from bookings.models import Booking


class PaymentViewSet(viewsets.ViewSet):
    
    @action(detail=False, methods=['post'], url_path='razorpay/create-order')
    def create_razorpay_order(self, request):
        """
        Create Razorpay order (disabled for now, but code is ready)
        """
        if not settings.RAZORPAY_ENABLED:
            return Response({
                'error': True,
                'message': 'Razorpay payment is currently disabled. Please use cash payment.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = RazorpayOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        booking_id = serializer.validated_data['booking_id']
        booking = get_object_or_404(Booking, id=booking_id)
        
        # Check if payment already exists
        if hasattr(booking, 'payment'):
            if booking.payment.status in ['captured', 'authorized']:
                return Response({
                    'error': True,
                    'message': 'Payment already completed for this booking'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize Razorpay client
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Create Razorpay order
        amount_in_paise = int(float(booking.total_amount) * 100)
        
        try:
            razorpay_order = client.order.create({
                'amount': amount_in_paise,
                'currency': 'INR',
                'receipt': f'booking_{booking.id}',
                'payment_capture': 1
            })
            
            # Create or update payment record
            payment, created = Payment.objects.update_or_create(
                booking=booking,
                defaults={
                    'razorpay_order_id': razorpay_order['id'],
                    'amount': booking.total_amount,
                    'currency': 'INR',
                    'status': 'created'
                }
            )
            
            return Response({
                'error': False,
                'message': 'Razorpay order created successfully',
                'data': {
                    'order_id': razorpay_order['id'],
                    'amount': booking.total_amount,
                    'currency': 'INR',
                    'key_id': settings.RAZORPAY_KEY_ID
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': True,
                'message': f'Failed to create Razorpay order: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='razorpay/verify')
    @transaction.atomic
    def verify_razorpay_payment(self, request):
        """
        Verify Razorpay payment signature (disabled for now, but code is ready)
        """
        if not settings.RAZORPAY_ENABLED:
            return Response({
                'error': True,
                'message': 'Razorpay payment is currently disabled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = RazorpayPaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Verify signature
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            f"{data['razorpay_order_id']}|{data['razorpay_payment_id']}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature != data['razorpay_signature']:
            return Response({
                'error': True,
                'message': 'Invalid payment signature'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update payment record
        try:
            payment = Payment.objects.get(razorpay_order_id=data['razorpay_order_id'])
            payment.razorpay_payment_id = data['razorpay_payment_id']
            payment.razorpay_signature = data['razorpay_signature']
            payment.status = 'captured'
            payment.save()
            
            # Update booking payment status
            booking = payment.booking
            booking.payment_status = 'completed'
            booking.payment_method = 'razorpay'
            booking.save()
            
            # Send payment receipt email & push
            from notifications.utils import EmailService, notify_payment_received
            EmailService.send_payment_receipt(payment)
            notify_payment_received(payment)
            
            return Response({
                'error': False,
                'message': 'Payment verified successfully',
                'data': {
                    'booking_id': booking.id,
                    'payment_status': 'completed'
                }
            })
            
        except Payment.DoesNotExist:
            return Response({
                'error': True,
                'message': 'Payment record not found'
            }, status=status.HTTP_404_NOT_FOUND)


class RefundViewSet(viewsets.ModelViewSet):
    """
    Refund management endpoints.
    - Users can request refunds
    - Staff can approve/reject/process/complete refunds
    """
    queryset = Refund.objects.select_related('payment__booking', 'requested_by', 'processed_by').all()
    serializer_class = RefundSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Refund.objects.select_related(
            'payment__booking', 'requested_by', 'processed_by'
        ).order_by('-requested_at')
        
        # Staff see all, users see only their own
        if user.is_staff:
            return qs
        return qs.filter(requested_by=user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Optional filters
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'error': False,
            'message': 'Refunds retrieved successfully',
            'data': serializer.data,
        })

    @action(detail=False, methods=['post'], url_path='request')
    @transaction.atomic
    def request_refund(self, request):
        """
        Request a refund for a payment.
        Body: { payment_id, amount, reason, reason_detail }
        """
        serializer = RefundRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        payment = get_object_or_404(Payment, id=data['payment_id'])

        # Validate payment status
        if payment.status not in ['captured', 'partially_refunded']:
            return Response({
                'error': True,
                'message': f'Cannot refund a payment with status: {payment.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate refund amount
        refundable = payment.refundable_amount
        if data['amount'] > refundable:
            return Response({
                'error': True,
                'message': f'Refund amount (₹{data["amount"]}) exceeds refundable amount (₹{refundable})'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check for duplicate pending refunds
        pending_refunds = Refund.objects.filter(
            payment=payment,
            status__in=['requested', 'approved']
        ).exists()
        if pending_refunds:
            return Response({
                'error': True,
                'message': 'A pending refund already exists for this payment'
            }, status=status.HTTP_400_BAD_REQUEST)

        refund = Refund.objects.create(
            payment=payment,
            amount=data['amount'],
            reason=data['reason'],
            reason_detail=data.get('reason_detail', ''),
            requested_by=request.user,
        )

        # Notify staff via push (if applicable)
        _notify_refund_requested(refund)

        refund_serializer = RefundSerializer(refund)
        return Response({
            'error': False,
            'message': 'Refund requested successfully. It will be reviewed by our team.',
            'data': refund_serializer.data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='process')
    @transaction.atomic
    def process_refund(self, request, pk=None):
        """
        Staff action to process a refund (approve/reject/process/complete).
        Body: { action, staff_notes?, razorpay_refund_id? }
        """
        refund = self.get_object()

        serializer = RefundProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        action_type = data['action']
        now = timezone.now()

        # Validate state transitions
        valid_transitions = {
            'approve': ['requested'],
            'reject': ['requested', 'approved'],
            'process': ['approved'],
            'complete': ['processed'],
        }

        if refund.status not in valid_transitions.get(action_type, []):
            return Response({
                'error': True,
                'message': f'Cannot {action_type} a refund with status: {refund.status}'
            }, status=status.HTTP_400_BAD_REQUEST)

        if action_type == 'approve':
            refund.status = 'approved'
            refund.processed_by = request.user
            if data.get('staff_notes'):
                refund.staff_notes = data['staff_notes']

        elif action_type == 'reject':
            refund.status = 'rejected'
            refund.processed_by = request.user
            refund.processed_at = now
            if data.get('staff_notes'):
                refund.staff_notes = data['staff_notes']

        elif action_type == 'process':
            refund.status = 'processed'
            refund.processed_by = request.user
            refund.processed_at = now
            if data.get('razorpay_refund_id'):
                refund.razorpay_refund_id = data['razorpay_refund_id']
            if data.get('staff_notes'):
                refund.staff_notes = data['staff_notes']

        elif action_type == 'complete':
            refund.status = 'completed'
            refund.completed_at = now
            if data.get('staff_notes'):
                refund.staff_notes = data['staff_notes']

            # Update payment status
            payment = refund.payment
            total_refunded = payment.total_refunded + refund.amount
            if total_refunded >= payment.amount:
                payment.status = 'refunded'
            else:
                payment.status = 'partially_refunded'
            payment.save(update_fields=['status', 'updated_at'])

        refund.save()

        # Notify user about refund status change
        _notify_refund_status_changed(refund)

        refund_serializer = RefundSerializer(refund)
        return Response({
            'error': False,
            'message': f'Refund {action_type}d successfully',
            'data': refund_serializer.data,
        })


def _notify_refund_requested(refund):
    """Notify about a new refund request."""
    from notifications.utils import send_push_notification
    # Could also notify staff here via dashboard WebSocket
    if refund.requested_by:
        send_push_notification(
            refund.requested_by,
            "Refund Requested",
            f"Your refund of ₹{refund.amount} for Booking #{refund.payment.booking_id} has been submitted.",
            data={'type': 'refund', 'refund_id': str(refund.id)}
        )


def _notify_refund_status_changed(refund):
    """Notify user when refund status changes."""
    from notifications.utils import send_push_notification

    status_messages = {
        'approved': f"Your refund of ₹{refund.amount} has been approved.",
        'rejected': f"Your refund of ₹{refund.amount} has been rejected. {refund.staff_notes}",
        'processed': f"Your refund of ₹{refund.amount} is being processed.",
        'completed': f"Your refund of ₹{refund.amount} has been completed! Check your account.",
    }

    if refund.status in status_messages and refund.requested_by:
        send_push_notification(
            refund.requested_by,
            f"Refund {refund.get_status_display()}",
            status_messages[refund.status],
            data={'type': 'refund', 'refund_id': str(refund.id)}
        )