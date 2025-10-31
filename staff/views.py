from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from bookings.models import Booking
from bookings.serializers import BookingDetailSerializer
from .permissions import IsStaffAPIKey


class StaffBookingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Staff endpoints to manage bookings
    """
    permission_classes = [IsStaffAPIKey]
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
        Body: { "status": "confirmed" | "in_progress" | "completed" | "cancelled" }
        """
        booking = self.get_object()
        new_status = request.data.get('status')
        
        if not new_status:
            return Response({
                'error': True,
                'message': 'status field is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        valid_statuses = ['pending', 'confirmed', 'in_progress', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            return Response({
                'error': True,
                'message': f'Invalid status. Valid options: {", ".join(valid_statuses)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        booking.booking_status = new_status
        
        # If completed, mark payment as completed (for cash payments)
        if new_status == 'completed' and booking.payment_method == 'cash':
            booking.payment_status = 'completed'
        
        booking.save()
        
        serializer = self.get_serializer(booking)
        
        return Response({
            'error': False,
            'message': f'Booking status updated to {new_status}',
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