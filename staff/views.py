from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from bookings.models import Booking, BookingStatusUpdate, Customer
from bookings.serializers import BookingDetailSerializer, BookingStatusUpdateSerializer
from feedback.models import IssueTicket
from rest_framework import permissions, serializers
from .permissions import IsStaffAuthenticated
from spare_parts.models import Order, ShipmentUpdate
from spare_parts.serializers import OrderSerializer, ShipmentUpdateSerializer
from authentication.models import StaffDirectory
from django.utils import timezone
from django.db.models import Count, Sum


class IssueTicketSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    assigned_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True, default='')

    class Meta:
        model = IssueTicket
        fields = [
            'id', 'user', 'user_name', 'booking', 'subject', 'description', 
            'status', 'priority', 'internal_notes', 'assigned_to', 'assigned_name',
            'resolved_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StaffDashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsStaffAuthenticated]

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """
        Main dashboard statistics for staff
        """
        today = timezone.now().date()
        
        # Today's Bookings
        today_bookings = Booking.objects.filter(appointment_date=today)
        pending_assignments = Booking.objects.filter(booking_status='confirmed', assigned_staff__isnull=True).count()
        
        # Tickets
        open_tickets = IssueTicket.objects.filter(status='open').count()
        urgent_tickets = IssueTicket.objects.filter(status='open', priority__in=['high', 'urgent']).count()
        
        # Revenue (Simple)
        total_revenue_today = Booking.objects.filter(
            appointment_date=today, 
            payment_status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Orders
        pending_orders = Order.objects.filter(status='paid').count()
        
        return Response({
            'error': False,
            'message': 'Dashboard stats retrieved',
            'data': {
                'today_bookings_count': today_bookings.count(),
                'pending_assignments': pending_assignments,
                'open_tickets': open_tickets,
                'urgent_tickets': urgent_tickets,
                'total_revenue_today': float(total_revenue_today),
                'pending_spare_orders': pending_orders,
            }
        })


class IssueTicketViewSet(viewsets.ModelViewSet):
    queryset = IssueTicket.objects.all()
    serializer_class = IssueTicketSerializer
    permission_classes = [IsStaffAuthenticated]
    
    def get_queryset(self):
        return IssueTicket.objects.all().order_by('-created_at')

    @action(detail=True, methods=['patch'], url_path='assign')
    def assign_ticket(self, request, pk=None):
        ticket = self.get_object()
        ticket.assigned_to = request.user
        ticket.status = 'investigating'
        ticket.save()
        return Response({'error': False, 'message': 'Ticket assigned to you'})

    @action(detail=True, methods=['patch'], url_path='resolve')
    def resolve_ticket(self, request, pk=None):
        ticket = self.get_object()
        ticket.status = 'resolved'
        ticket.resolved_at = timezone.now()
        ticket.save()
        return Response({'error': False, 'message': 'Ticket marked as resolved'})

class StaffBookingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Staff endpoints to manage bookings
    """
    permission_classes = [permissions.IsAuthenticated, IsStaffAuthenticated]
    queryset = Booking.objects.select_related(
        'customer',
        'vehicle_model__vehicle_brand__vehicle_type'
    ).prefetch_related('booking_services__service__service_category').all()
    serializer_class = BookingDetailSerializer
    
    def list(self, request, *args, **kwargs):
        """
        Get all bookings with optional filters
        Query params: status, date, search
        """
        queryset = self.get_queryset()
        
        # Filter by status
        booking_status = request.query_params.get('status')
        if booking_status:
            queryset = queryset.filter(booking_status=booking_status)
        
        # Filter by date
        date = request.query_params.get('date')
        if date:
            queryset = queryset.filter(appointment_date=date)
        
        # Search by customer name or phone
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(customer__name__icontains=search) |
                Q(customer__phone__icontains=search)
            )
        
        # Order by appointment date and time
        queryset = queryset.order_by('appointment_date', 'appointment_time', '-created_at')
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'error': False,
            'message': 'Bookings retrieved successfully',
            'data': serializer.data,
            'count': queryset.count()
        })
    
    def retrieve(self, request, *args, **kwargs):
        """
        Get single booking details
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'error': False,
            'message': 'Booking details retrieved successfully',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        """
        Update booking status
        Body: { "status", "note"?, "lat"?, "lng"? }
        """
        booking = self.get_object()
        new_status = request.data.get('status')
        note = request.data.get('note', '')
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        
        if not new_status:
            return Response({'error': True, 'message': 'status is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_statuses = [c[0] for c in Booking.BOOKING_STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response({'error': True, 'message': f'Invalid status. Valid: {", ".join(valid_statuses)}'}, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = booking.booking_status
        booking.booking_status = new_status
        
        # Automatic logic for specific statuses
        if new_status == 'completed' and booking.payment_method == 'cash':
            booking.payment_status = 'completed'
        
        booking.save()
        
        # Record history
        BookingStatusUpdate.objects.create(
            booking=booking,
            status=new_status,
            note=note or f"Status changed from {old_status} to {new_status}",
            location_lat=lat,
            location_lng=lng,
            updated_by=request.user
        )
        
        # Notifications
        from notifications.utils import notify_booking_status_update
        notify_booking_status_update(booking)
        
        if new_status == 'completed':
            from notifications.utils import EmailService
            EmailService.send_invoice(booking)
        
        return Response({
            'error': False,
            'message': f'Booking status updated to {new_status}',
            'data': self.get_serializer(booking).data
        })

    @action(detail=True, methods=['patch'], url_path='assign-mechanic')
    def assign_mechanic(self, request, pk=None):
        """
        Assign a staff member to a booking
        Body: { "staff_id": int }
        """
        booking = self.get_object()
        staff_id = request.data.get('staff_id')
        
        if not staff_id:
            return Response({'error': True, 'message': 'staff_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            staff = StaffDirectory.objects.get(id=staff_id, is_active=True)
        except StaffDirectory.DoesNotExist:
            return Response({'error': True, 'message': 'Invalid or inactive staff ID'}, status=status.HTTP_404_NOT_FOUND)
            
        booking.assigned_staff = staff
        booking.booking_status = 'assigned'
        booking.save()
        
        # Log assignment
        BookingStatusUpdate.objects.create(
            booking=booking,
            status='assigned',
            note=f"Assigned to {staff.name or staff.identifier}",
            updated_by=request.user
        )
        
        # Notify customer
        from notifications.utils import notify_mechanic_assigned
        notify_mechanic_assigned(booking)
        
        return Response({
            'error': False,
            'message': f'Mechanic {staff.name} assigned successfully',
            'data': self.get_serializer(booking).data
        })

    @action(detail=False, methods=['get'], url_path='my-bookings')
    def my_bookings(self, request):
        """
        Get bookings assigned to the current staff user
        """
        try:
            staff_profile = request.user.staff_profile
        except AttributeError:
            return Response({'error': True, 'message': 'User has no staff profile'}, status=status.HTTP_403_FORBIDDEN)
            
        queryset = self.get_queryset().filter(assigned_staff=staff_profile)
        
        # Filter by status if provided
        status_param = request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(booking_status=status_param)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'error': False,
            'message': 'Your assigned bookings retrieved successfully',
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'], url_path='stats')
    def get_stats(self, request):
        """
        Get booking statistics
        """
        queryset = self.get_queryset()
        
        total_bookings = queryset.count()
        pending = queryset.filter(booking_status='pending').count()
        confirmed = queryset.filter(booking_status='confirmed').count()
        in_progress = queryset.filter(booking_status='in_progress').count()
        completed = queryset.filter(booking_status='completed').count()
        cancelled = queryset.filter(booking_status='cancelled').count()
        
        # Payment stats
        payment_pending = queryset.filter(payment_status='pending').count()
        payment_completed = queryset.filter(payment_status='completed').count()
        
        return Response({
            'error': False,
            'message': 'Statistics retrieved successfully',
            'data': {
                'total_bookings': total_bookings,
                'booking_status': {
                    'pending': pending,
                    'confirmed': confirmed,
                    'in_progress': in_progress,
                    'completed': completed,
                    'cancelled': cancelled
                },
                'payment_status': {
                    'pending': payment_pending,
                    'completed': payment_completed
                }
            }
        })


class StaffOrderViewSet(viewsets.ModelViewSet):
    """
    Staff endpoints to manage spare part orders
    """
    permission_classes = [permissions.IsAuthenticated, IsStaffAuthenticated]
    queryset = Order.objects.select_related('user').prefetch_related('items__spare_part', 'shipment_updates').all()
    serializer_class = OrderSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Filter by status
        status_param = request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Search by customer name or phone
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(customer_name__icontains=search) |
                Q(phone__icontains=search)
            )
        
        queryset = queryset.order_by('-created_at')
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'error': False,
            'message': 'Orders retrieved successfully',
            'data': serializer.data,
            'count': queryset.count()
        })

    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        """
        Update order status
        Body: { "status": "confirmed" | "shipped" | "delivered" | etc }
        """
        order = self.get_object()
        new_status = request.data.get('status')
        
        if not new_status:
            return Response({'error': True, 'message': 'status is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = order.status
        order.status = new_status
        
        if new_status == 'shipped' and not order.shipped_at:
            order.shipped_at = timezone.now()
        elif new_status == 'delivered' and not order.delivered_at:
            order.delivered_at = timezone.now()
            order.payment_status = 'cash_paid' # Assuming cash on delivery
            
        order.save()
        
        # Add shipment update automatically
        ShipmentUpdate.objects.create(
            order=order,
            status=new_status,
            note=f"Order status updated from {old_status} to {new_status}",
            created_by=request.user
        )
        
        # Send notification
        from notifications.utils import notify_order_status_update
        notify_order_status_update(order)
        
        return Response({
            'error': False,
            'message': f'Order status updated to {new_status}',
            'data': self.get_serializer(order).data
        })

    @action(detail=True, methods=['patch'], url_path='update-tracking')
    def update_tracking(self, request, pk=None):
        """
        Update tracking information
        Body: { "tracking_number", "courier_name", "courier_tracking_url"?, "estimated_delivery"? }
        """
        order = self.get_object()
        order.tracking_number = request.data.get('tracking_number', order.tracking_number)
        order.courier_name = request.data.get('courier_name', order.courier_name)
        order.courier_tracking_url = request.data.get('courier_tracking_url', order.courier_tracking_url)
        
        est_delivery = request.data.get('estimated_delivery')
        if est_delivery:
            order.estimated_delivery = est_delivery
            
        order.save()
        
        return Response({
            'error': False,
            'message': 'Tracking information updated',
            'data': self.get_serializer(order).data
        })

    @action(detail=True, methods=['post'], url_path='add-shipment-update')
    def add_shipment_update(self, request, pk=None):
        """
        Add a manual shipment update
        Body: { "status", "location"?, "note"? }
        """
        order = self.get_object()
        shipment_status = request.data.get('status')
        
        if not shipment_status:
            return Response({'error': True, 'message': 'status is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        update = ShipmentUpdate.objects.create(
            order=order,
            status=shipment_status,
            location=request.data.get('location', ''),
            note=request.data.get('note', ''),
            created_by=request.user
        )
        
        return Response({
            'error': False,
            'message': 'Shipment update added successfully',
            'data': ShipmentUpdateSerializer(update).data
        })