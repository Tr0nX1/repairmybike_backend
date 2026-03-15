from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Customer, Booking, BookingService
from .serializers import (
    CustomerSerializer, BookingCreateSerializer,
    BookingListSerializer, BookingDetailSerializer
)
from services.models import ServicePricing
from vehicles.models import VehicleModel
from subscriptions.models import Subscription


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
            # Filter bookings by the authenticated user's phone number
            customer = Customer.objects.get(phone=request.user.phone_number)
            queryset = self.get_queryset().filter(customer=customer)
            serializer = self.get_serializer(queryset, many=True)
            
            return Response({
                'error': False,
                'message': 'Booking history retrieved successfully',
                'data': serializer.data
            })
        except Customer.DoesNotExist:
            return Response({
                'error': False,
                'message': 'No bookings found',
                'data': []
            })
    
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

        # Create booking
        booking = Booking.objects.create(
            customer=customer,
            vehicle_model=vehicle_model,
            service_location=data['service_location'],
            address=data.get('address', ''),
            address_details=data.get('address_details'),
            appointment_date=data['appointment_date'],
            appointment_time=data['appointment_time'],
            total_amount=total_amount,
            payment_method=data.get('payment_method', 'cash'),
            subscription=subscription,
            notes=data.get('notes', '')
        )

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
        
        return Response({
            'error': False,
            'message': 'Booking created successfully',
            'data': response_serializer.data
        }, status=status.HTTP_201_CREATED)