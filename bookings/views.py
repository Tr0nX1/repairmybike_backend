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
        phone = request.query_params.get('phone')
        
        if not phone:
            return Response({
                'error': True,
                'message': 'phone query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            customer = Customer.objects.get(phone=phone)
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
                'message': 'No bookings found for this phone number',
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
        serializer.is_valid(raise_exception=True)
        
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
        
        # Create booking
        booking = Booking.objects.create(
            customer=customer,
            vehicle_model=vehicle_model,
            service_location=data['service_location'],
            address=data.get('address', ''),
            appointment_date=data['appointment_date'],
            appointment_time=data['appointment_time'],
            total_amount=total_amount,
            payment_method=data.get('payment_method', 'cash'),
            notes=data.get('notes', '')
        )
        
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