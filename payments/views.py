from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
import razorpay
import hmac
import hashlib
from .models import Payment
from .serializers import (
    PaymentSerializer,
    RazorpayOrderCreateSerializer,
    RazorpayPaymentVerifySerializer
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