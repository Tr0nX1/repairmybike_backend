from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction, models
from django.shortcuts import get_object_or_404
from .models import Customer, Booking, BookingService
from .serializers import (
    CustomerSerializer, BookingCreateSerializer,
    BookingListSerializer, BookingDetailSerializer
)
from services.models import ServicePricing
from vehicles.models import VehicleModel
from subscriptions.models import Subscription
from promotions.models import Coupon, CouponUsage


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related(
        'customer',
        'vehicle_model__vehicle_brand__vehicle_type'
    ).prefetch_related('booking_services__service__service_category').all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BookingCreateSerializer
        elif self.action == 'retrieve':
            return BookingDetailSerializer
        return BookingListSerializer
    
    def list(self, request, *args, **kwargs):
        # Strict security: Only logged-in users can view their bookings
        if not request.user.is_authenticated:
            return Response({
                'error': True,
                'message': 'Authentication required to view bookings'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            # First, check if a Customer entry exists for this user's phone
            customer = Customer.objects.filter(phone=request.user.phone_number).first()
            
            if not customer:
                # If no customer profile exists, it means they have no bookings yet.
                # We return a successful empty list instead of letting it fail.
                return Response({
                    'error': False,
                    'message': 'No bookings found',
                    'data': []
                })

            queryset = self.get_queryset().filter(customer=customer)
            serializer = self.get_serializer(queryset, many=True)
            
            return Response({
                'error': False,
                'message': 'Booking history retrieved successfully',
                'data': serializer.data
            })
        except Exception as e:
            logger.error(f"Error fetching bookings: {e}")
            return Response({
                'error': True,
                'message': 'Failed to retrieve booking history'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'error': False,
            'message': 'Booking details retrieved successfully',
            'data': serializer.data
        })
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        # Validate and return consistent error response instead of DRF default
        if not serializer.is_valid():
            return Response({
                'error': True,
                'message': 'Invalid booking data',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        
        # Verify vehicle model exists
        try:
            vehicle_model = VehicleModel.objects.get(id=data['vehicle_model_id'])
        except VehicleModel.DoesNotExist:
            return Response({
                'error': True,
                'message': 'Invalid vehicle model'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create customer
        customer, created = Customer.objects.get_or_create(
            phone=data['customer_phone'],
            defaults={
                'name': data['customer_name'],
                'email': data.get('customer_email', '')
            }
        )
        
        # If customer exists, update name and email
        if not created:
            customer.name = data['customer_name']
            if data.get('customer_email'):
                customer.email = data['customer_email']
            customer.save()
        
        # Calculate total amount and validate services
        total_amount = 0
        service_prices = {}
        
        for service_id in data['service_ids']:
            try:
                pricing = ServicePricing.objects.get(
                    service_id=service_id,
                    vehicle_model_id=data['vehicle_model_id']
                )
                service_prices[service_id] = pricing.price
                total_amount += pricing.price
            except ServicePricing.DoesNotExist:
                return Response({
                    'error': True,
                    'message': f'Service pricing not found for service ID {service_id} and selected vehicle'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Optional subscription linkage
        subscription = None
        if data.get('subscription_id'):
            try:
                subscription = Subscription.objects.select_related('plan').get(id=data['subscription_id'])
            except Subscription.DoesNotExist:
                return Response({
                    'error': True,
                    'message': 'Invalid subscription'
                }, status=status.HTTP_400_BAD_REQUEST)
            # Enforce remaining visits if plan includes visit limits
            included = subscription.plan.included_visits or 0
            consumed = subscription.visits_consumed or 0
            if included > 0 and consumed >= included:
                return Response({
                    'error': True,
                    'message': 'No subscription visits remaining'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Optional Coupon Validation
        coupon = None
        discount_amount = 0
        if data.get('coupon_code'):
            try:
                coupon = Coupon.objects.get(code__iexact=data['coupon_code'])
                is_valid, error_msg = coupon.is_valid(user=request.user if request.user.is_authenticated else None, amount=float(total_amount))
                if not is_valid:
                    return Response({'error': True, 'message': error_msg}, status=status.HTTP_400_BAD_REQUEST)
                
                discount_amount = coupon.calculate_discount(float(total_amount))
            except Coupon.DoesNotExist:
                return Response({'error': True, 'message': 'Invalid coupon code'}, status=status.HTTP_400_BAD_REQUEST)

        # Optional Loyalty Points Redemption (1 point = 1 INR)
        loyalty_discount = 0
        points_to_redeem = 0
        if data.get('use_loyalty_points') and request.user.is_authenticated:
            user = request.user
            if user.loyalty_points > 0:
                # Can redeem up to the total amount remaining after coupon
                max_redeemable = float(total_amount) - float(discount_amount)
                points_to_redeem = min(user.loyalty_points, int(max_redeemable))
                loyalty_discount = float(points_to_redeem)
                
                if points_to_redeem > 0:
                    from authentication.models import LoyaltyTransaction
                    with transaction.atomic():
                        # Record redemption transaction
                        LoyaltyTransaction.objects.create(
                            user=user,
                            points=-points_to_redeem,
                            transaction_type='redeemed',
                            description=f"Points redeemed for Booking",
                            # booking will be linked after creation
                        )
                        # Update user balance
                        user.loyalty_points -= points_to_redeem
                        user.save(update_fields=['loyalty_points', 'updated_at'])

        # Idempotency Check
        idempotency_key = data.get('idempotency_key')
        if idempotency_key:
            existing_booking = Booking.objects.filter(idempotency_key=idempotency_key).first()
            if existing_booking:
                response_serializer = BookingDetailSerializer(existing_booking)
                return Response({
                    'error': False,
                    'message': 'Booking retrieved (Idempotent)',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)

        # Handle UserAddress Linkage & Snapshotting
        user_address = None
        user_address_id = data.get('user_address_id')
        if user_address_id:
            from authentication.models import UserAddress
            try:
                user_address = UserAddress.objects.get(id=user_address_id)
                # Auto-snapshot from the linked address if not manually provided
                if not data.get('address_details'):
                    data['address_details'] = {
                        'full_name': user_address.full_name,
                        'phone_number': user_address.phone_number,
                        'address_type': user_address.address_type,
                        'flat_house_no': user_address.flat_house_no,
                        'area_street': user_address.area_street,
                        'landmark': user_address.landmark,
                        'pincode': user_address.pincode,
                        'town_city': user_address.town_city,
                        'state': user_address.state,
                        'latitude': float(user_address.latitude) if user_address.latitude else None,
                        'longitude': float(user_address.longitude) if user_address.longitude else None,
                    }
                if not data.get('address'):
                    data['address'] = f"{user_address.flat_house_no}, {user_address.area_street}, {user_address.town_city}"
            except UserAddress.DoesNotExist:
                return Response({'error': True, 'message': 'Invalid user address ID'}, status=status.HTTP_400_BAD_REQUEST)

        # Create booking
        booking = Booking.objects.create(
            customer=customer,
            vehicle_model=vehicle_model,
            service_location=data['service_location'],
            address=data.get('address', ''),
            address_details=data.get('address_details'),
            appointment_date=data['appointment_date'],
            appointment_time=data['appointment_time'],
            total_amount=float(total_amount) - float(discount_amount) - float(loyalty_discount),
            discount_amount=float(discount_amount) + float(loyalty_discount),
            applied_coupon=coupon,
            payment_method=data.get('payment_method', 'cash'),
            subscription=subscription,
            notes=data.get('notes', f"Loyalty points used: {points_to_redeem}" if points_to_redeem else ''),
            user_address=user_address,
            idempotency_key=idempotency_key
        )
        
        # Link transaction to booking
        if points_to_redeem:
            loyalty_txn = LoyaltyTransaction.objects.filter(
                user=request.user, 
                booking__isnull=True, 
                transaction_type='redeemed'
            ).order_by('-created_at').first()
            if loyalty_txn:
                loyalty_txn.booking = booking
                loyalty_txn.save(update_fields=['booking'])
        
        # If coupon used, record usage and increment count
        if coupon:
            CouponUsage.objects.create(
                coupon=coupon,
                user=request.user if request.user.is_authenticated else None,
                booking=booking,
                discount_applied=discount_amount
            )
            coupon.usage_count += 1
            coupon.save()

        # Sync address to user profile if authenticated
        if request.user.is_authenticated and data.get('address_details'):
            from authentication.models import UserAddress
            addr_data = data['address_details']
            
            # Simple check to avoid duplicates for the same user
            existing_addr = UserAddress.objects.filter(
                user=request.user,
                flat_house_no=addr_data.get('flat_house_no', ''),
                area_street=addr_data.get('area_street', ''),
                pincode=addr_data.get('pincode', ''),
            ).first()
            
            if not existing_addr:
                # If it's a new unique address, save it to profile and make it default
                UserAddress.objects.filter(user=request.user, is_default=True).update(is_default=False)
                UserAddress.objects.create(
                    user=request.user,
                    full_name=addr_data.get('full_name', data['customer_name']),
                    phone_number=addr_data.get('phone_number', data['customer_phone']),
                    flat_house_no=addr_data.get('flat_house_no', ''),
                    area_street=addr_data.get('area_street', ''),
                    landmark=addr_data.get('landmark', ''),
                    pincode=addr_data.get('pincode', ''),
                    town_city=addr_data.get('town_city', ''),
                    state=addr_data.get('state', ''),
                    is_default=True,
                )
            elif not existing_addr.is_default:
                # If address exists but is not default, make it default
                UserAddress.objects.filter(user=request.user, is_default=True).update(is_default=False)
                existing_addr.is_default = True
                existing_addr.save()
        
        # Create booking services
        for service_id in data['service_ids']:
            BookingService.objects.create(
                booking=booking,
                service_id=service_id,
                price=service_prices[service_id]
            )
        
        # Fetch created booking with all relations
        booking = Booking.objects.select_related(
            'customer',
            'vehicle_model__vehicle_brand__vehicle_type'
        ).prefetch_related('booking_services__service__service_category').get(id=booking.id)
        
        response_serializer = BookingDetailSerializer(booking)
        
        # Send confirmation email
        from notifications.utils import EmailService
        EmailService.send_booking_confirmation(booking)
        
        return Response({
            'error': False,
            'message': 'Booking created successfully',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def live_location(self, request, pk=None):
        """Update and broadcast mechanic's live location."""
        booking = self.get_object()
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        
        if not lat or not lng:
            return Response({'error': True, 'message': 'lat and lng are required'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Broadcast to WebSocket
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        from django.utils import timezone
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'tracking_{booking.id}',
            {
                'type': 'tracking_message',
                'message': {
                    'booking_id': booking.id,
                    'lat': float(lat),
                    'lng': float(lng),
                    'timestamp': timezone.now().isoformat()
                }
            }
        )
        
        return Response({'error': False, 'message': 'Location broadcasted'})