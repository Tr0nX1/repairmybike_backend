from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from repairmybike.fcm import send_push_notification
from .models import Customer, Booking, BookingPart, BookingService
from .serializers import (
    CustomerSerializer, BookingCreateSerializer,
    BookingListSerializer, BookingDetailSerializer,
    FeedbackSerializer
)
from services.models import ServicePricing
from vehicles.models import VehicleModel
from subscriptions.models import Subscription
from spare_parts.models import SparePart
from staff.models import ActivityLog
from .models import Feedback

User = get_user_model()


class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.select_related('user', 'booking', 'booking__customer').all()
    serializer_class = FeedbackSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Feedback.objects.select_related('user', 'booking', 'booking__customer').all()
        return Feedback.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()


class IsBookingOwnerOrStaff(permissions.BasePermission):
    """
    Permission to check if user owns the booking or is staff/admin.
    Customers can only access their own bookings.
    Staff/Admin can access all bookings.
    """
    
    def has_object_permission(self, request, view, obj):
        # Staff and admins have full access
        if request.user and (request.user.is_staff or request.user.is_superuser):
            return True
        
        # Authenticated customers can only access their own bookings
        if request.user and request.user.is_authenticated:
            try:
                customer = Customer.objects.get(phone=request.user.phone_number)
                return obj.customer.id == customer.id
            except Customer.DoesNotExist:
                return False
        
        return False


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
    
    def get_queryset(self):
        """
        Filter bookings based on user authentication and role.
        - Authenticated customers: only their own bookings
        - Staff/Admin: all bookings
        - Anonymous users: no access
        """
        user = self.request.user
        
        # Anonymous users get empty queryset
        if not user or not user.is_authenticated:
            return Booking.objects.none()
        
        # Staff and admins see all bookings
        if user.is_staff or user.is_superuser:
            return self.queryset
        
        # Authenticated customers see only their bookings
        try:
            customer = Customer.objects.get(phone=user.phone_number)
            return self.queryset.filter(customer=customer)
        except Customer.DoesNotExist:
            return Booking.objects.none()
    
    def get_permissions(self):
        """
        Assign permission classes based on action.
        list/create: requires authentication
        retrieve/update/partial_update/destroy: requires authentication + ownership check
        approve-parts/reject-parts/cancel: requires authentication + ownership check
        """
        permission_classes = [permissions.IsAuthenticated]
        
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy', 
                           'approve_parts', 'reject_parts', 'cancel', 'assign_mechanic']:
            permission_classes.append(IsBookingOwnerOrStaff)
        
        return [permission() for permission in permission_classes]

    def _user_can_manage_mechanics(self, user):
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.is_staff or getattr(user, 'is_manager', False))
        )
    
    def _user_can_access_booking(self, request, booking):
        """
        Check if the authenticated user can access this booking.
        Used as fallback for extra safety verification.
        """
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        try:
            customer = Customer.objects.get(phone=user.phone_number)
            return booking.customer.id == customer.id
        except Customer.DoesNotExist:
            return False
    
    def list(self, request, *args, **kwargs):
        """
        List bookings - filtered by get_queryset() based on user role.
        Only authenticated users can access their bookings.
        """
        if not request.user.is_authenticated:
            return Response({
                'error': True,
                'message': 'Authentication required to view bookings'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'error': False,
            'message': 'Booking history retrieved successfully',
            'data': serializer.data
        })
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific booking.
        Enforces ownership check via get_object() and IsBookingOwnerOrStaff permission.
        """
        instance = self.get_object()  # This enforces get_queryset() filter
        
        # Additional explicit permission check for clarity
        if not self._user_can_access_booking(request, instance):
            return Response(
                {'error': True, 'message': 'You do not have permission to view this booking'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance)
        return Response({
            'error': False,
            'message': 'Booking details retrieved successfully',
            'data': serializer.data
        })
    
    def update(self, request, *args, **kwargs):
        """
        Full update of a booking.
        Only staff can update bookings (restricted by permission classes).
        """
        instance = self.get_object()  # This enforces get_queryset() filter
        
        if not self._user_can_access_booking(request, instance):
            return Response(
                {'error': True, 'message': 'You do not have permission to update this booking'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {'error': True, 'message': 'Only staff can update bookings'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """
        Partial update of a booking.
        Only staff can update bookings (restricted by permission classes).
        """
        instance = self.get_object()  # This enforces get_queryset() filter
        
        if not self._user_can_access_booking(request, instance):
            return Response(
                {'error': True, 'message': 'You do not have permission to update this booking'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {'error': True, 'message': 'Only staff can update bookings'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a booking.
        Only staff can delete bookings.
        """
        instance = self.get_object()  # This enforces get_queryset() filter
        
        if not self._user_can_access_booking(request, instance):
            return Response(
                {'error': True, 'message': 'You do not have permission to delete this booking'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {'error': True, 'message': 'Only staff can delete bookings'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)
    def _get_part_ids(self, request):
        part_ids = request.data.get('part_ids')
        if not isinstance(part_ids, list) or not part_ids:
            return None
        try:
            return [int(part_id) for part_id in part_ids]
        except (TypeError, ValueError):
            return None

    @action(detail=True, methods=['patch'], url_path='assign-mechanic')
    @transaction.atomic
    def assign_mechanic(self, request, pk=None):
        if not self._user_can_manage_mechanics(request.user):
            return Response(
                {'error': True, 'message': 'Only admins or managers can assign mechanics'},
                status=status.HTTP_403_FORBIDDEN
            )

        mechanic_id = request.data.get('mechanic_id')
        if not mechanic_id:
            return Response(
                {'error': True, 'message': 'mechanic_id field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            booking = Booking.objects.select_for_update().get(pk=pk)
        except Booking.DoesNotExist:
            return Response(
                {'error': True, 'message': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            mechanic = User.objects.get(id=mechanic_id, is_staff=True, is_active=True)
        except User.DoesNotExist:
            return Response(
                {'error': True, 'message': 'Mechanic not found or is not an active staff user'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_mechanic_id = booking.mechanic_id
        old_mechanic_name = booking.mechanic.get_full_name() if booking.mechanic else None
        booking.mechanic = mechanic
        if booking.booking_status == 'pending':
            booking.booking_status = 'assigned'
        booking.save(update_fields=['mechanic', 'booking_status', 'updated_at'])

        mechanic_name = mechanic.get_full_name() or mechanic.username
        ActivityLog.objects.create(
            user=request.user,
            action_type='mechanic_assigned',
            description=f"Assigned {mechanic_name} to Booking #{booking.id}",
            content_object=booking,
            metadata={
                'old_mechanic_id': old_mechanic_id,
                'old_mechanic_name': old_mechanic_name,
                'new_mechanic_id': mechanic.id,
                'new_mechanic_name': mechanic_name,
                'booking_id': booking.id,
                'old_value': old_mechanic_id,
                'new_value': mechanic.id,
                'status': booking.booking_status,
            }
        )

        send_push_notification(
            mechanic,
            'New booking assigned',
            f'New booking assigned: #{booking.id}',
            data={'booking_id': str(booking.id), 'type': 'booking_assigned'}
        )

        booking = self.queryset.get(id=booking.id)
        return Response({
            'error': False,
            'message': 'Mechanic assigned successfully',
            'data': BookingDetailSerializer(booking).data,
        })

    @action(detail=True, methods=['post'], url_path='approve-parts')
    @transaction.atomic
    def approve_parts(self, request, pk=None):
        """
        Approve parts for a booking.
        Only customers/staff who own the booking can approve.
        """
        try:
            booking = Booking.objects.select_for_update().get(pk=pk)
        except Booking.DoesNotExist:
            return Response(
                {'error': True, 'message': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify ownership/access before proceeding
        if not self._user_can_access_booking(request, booking):
            return Response(
                {'error': True, 'message': 'You do not have permission to approve parts for this booking'},
                status=status.HTTP_403_FORBIDDEN
            )

        part_ids = self._get_part_ids(request)
        if not part_ids:
            return Response({'error': True, 'message': 'part_ids must be a non-empty array'}, status=status.HTTP_400_BAD_REQUEST)

        booking_parts = BookingPart.objects.select_for_update().select_related('spare_part').filter(
            id__in=part_ids,
            booking=booking,
        )
        if booking_parts.count() != len(set(part_ids)):
            return Response({'error': True, 'message': 'One or more booking parts were not found'}, status=status.HTTP_404_NOT_FOUND)

        approved_at = timezone.now()
        for booking_part in booking_parts:
            old_status = booking_part.approval_status
            booking_part.approval_status = BookingPart.APPROVAL_APPROVED
            booking_part.approved_by = request.user
            booking_part.approved_at = approved_at
            booking_part.save(update_fields=['approval_status', 'approved_by', 'approved_at'])
            ActivityLog.objects.create(
                user=request.user,
                action_type='part_approved',
                description=f"Approved {booking_part.spare_part.name} for Booking #{booking.id}",
                content_object=booking_part,
                metadata={
                    'old_value': old_status,
                    'new_value': booking_part.approval_status,
                    'booking_id': booking.id,
                    'booking_part_id': booking_part.id,
                    'part_id': booking_part.spare_part_id,
                    'quantity': booking_part.quantity,
                    'amount': str(booking_part.total_price),
                    'unit_price': str(booking_part.unit_price),
                }
            )

        return Response({
            'error': False,
            'message': 'Parts approved successfully',
            'data': BookingDetailSerializer(booking).data,
        })

    @action(detail=True, methods=['post'], url_path='reject-parts')
    @transaction.atomic
    def reject_parts(self, request, pk=None):
        """
        Reject parts for a booking.
        Only customers/staff who own the booking can reject.
        """
        try:
            booking = Booking.objects.select_for_update().get(pk=pk)
        except Booking.DoesNotExist:
            return Response(
                {'error': True, 'message': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify ownership/access before proceeding
        if not self._user_can_access_booking(request, booking):
            return Response(
                {'error': True, 'message': 'You do not have permission to reject parts for this booking'},
                status=status.HTTP_403_FORBIDDEN
            )

        part_ids = self._get_part_ids(request)
        if not part_ids:
            return Response({'error': True, 'message': 'part_ids must be a non-empty array'}, status=status.HTTP_400_BAD_REQUEST)

        booking_parts = BookingPart.objects.select_for_update().select_related('spare_part').filter(
            id__in=part_ids,
            booking=booking,
        )
        if booking_parts.count() != len(set(part_ids)):
            return Response({'error': True, 'message': 'One or more booking parts were not found'}, status=status.HTTP_404_NOT_FOUND)

        rejected_total = 0
        for booking_part in booking_parts:
            old_status = booking_part.approval_status
            if booking_part.approval_status != BookingPart.APPROVAL_REJECTED:
                rejected_total += booking_part.total_price
            booking_part.approval_status = BookingPart.APPROVAL_REJECTED
            booking_part.approved_by = request.user
            booking_part.approved_at = timezone.now()
            booking_part.save(update_fields=['approval_status', 'approved_by', 'approved_at'])
            ActivityLog.objects.create(
                user=request.user,
                action_type='part_rejected',
                description=f"Rejected {booking_part.spare_part.name} for Booking #{booking.id}",
                content_object=booking_part,
                metadata={
                    'old_value': old_status,
                    'new_value': booking_part.approval_status,
                    'booking_id': booking.id,
                    'booking_part_id': booking_part.id,
                    'part_id': booking_part.spare_part_id,
                    'quantity': booking_part.quantity,
                    'amount': str(booking_part.total_price),
                    'unit_price': str(booking_part.unit_price),
                }
            )

        if rejected_total:
            booking.total_amount -= rejected_total
            if booking.total_amount < 0:
                booking.total_amount = 0
            booking.save(update_fields=['total_amount', 'updated_at'])

        return Response({
            'error': False,
            'message': 'Parts rejected successfully',
            'data': BookingDetailSerializer(booking).data,
        })

    @action(detail=True, methods=['post'], url_path='cancel')
    @transaction.atomic
    def cancel(self, request, pk=None):
        """
        Cancel a booking.
        Only customers/staff who own the booking can cancel.
        """
        try:
            booking = Booking.objects.select_for_update().get(pk=pk)
        except Booking.DoesNotExist:
            return Response(
                {'error': True, 'message': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        old_status = booking.booking_status
        
        # Verify ownership/access before proceeding
        if not self._user_can_access_booking(request, booking):
            return Response(
                {'error': True, 'message': 'You do not have permission to cancel this booking'},
                status=status.HTTP_403_FORBIDDEN
            )

        if booking.booking_status == 'cancelled':
            return Response({'error': True, 'message': 'Booking is already cancelled'}, status=status.HTTP_400_BAD_REQUEST)

        if booking.stock_deducted:
            approved_parts = booking.booking_parts.filter(approval_status=BookingPart.APPROVAL_APPROVED)
            for booking_part in approved_parts:
                part = SparePart.objects.select_for_update().get(id=booking_part.spare_part_id)
                part.stock_qty += booking_part.quantity
                part.in_stock = part.stock_qty > 0
                part.save(update_fields=['stock_qty', 'in_stock', 'updated_at'])
                ActivityLog.objects.create(
                    user=request.user,
                    action_type='stock_reversed',
                    description=f"Reversed {booking_part.quantity}x {part.name} for cancelled Booking #{booking.id}",
                    content_object=booking_part,
                    metadata={
                        'old_value': booking.stock_deducted,
                        'new_value': False,
                        'booking_id': booking.id,
                        'booking_part_id': booking_part.id,
                        'part_id': part.id,
                        'quantity': booking_part.quantity,
                        'amount': str(booking_part.total_price),
                        'stock_qty': part.stock_qty,
                    }
                )
            booking.stock_deducted = False

        booking.booking_status = 'cancelled'
        booking.save(update_fields=['booking_status', 'stock_deducted', 'updated_at'])

        ActivityLog.objects.create(
            user=request.user,
            action_type='booking_cancelled',
            description=f"Booking #{booking.id} cancelled",
            content_object=booking,
            metadata={
                'old_value': old_status,
                'new_value': booking.booking_status,
                'booking_id': booking.id,
                'stock_deducted_reversed': not booking.stock_deducted,
            }
        )

        return Response({
            'error': False,
            'message': 'Booking cancelled successfully',
            'data': BookingDetailSerializer(booking).data,
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
        
        vehicle_model_id = data.get('vehicle_model_id')
        if not vehicle_model_id:
            if request.user.is_authenticated and request.user.default_vehicle_id:
                vehicle_model_id = request.user.default_vehicle_id
            else:
                return Response({
                    'error': True,
                    'message': 'vehicle_model_id is required. No default vehicle set on account.'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Verify vehicle model exists
        try:
            vehicle_model = VehicleModel.objects.get(id=vehicle_model_id)
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
                    vehicle_model_id=vehicle_model_id
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
            appointment_date=data['appointment_date'],
            appointment_time=data['appointment_time'],
            total_amount=total_amount,
            payment_method=data.get('payment_method', 'cash'),
            subscription=subscription,
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
