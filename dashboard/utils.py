import logging
import time
from django.utils import timezone
from django.db.models import Sum, Q
from bookings.models import Booking
from spare_parts.models import Order, SparePart

logger = logging.getLogger(__name__)

def get_dashboard_metrics():
    start_time = time.time()
    today = timezone.now().date()
    
    try:
        # 1. Revenue Metrics
        booking_revenue = Booking.objects.filter(
            appointment_date=today,
            payment_status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        order_revenue = Order.objects.filter(
            created_at__date=today,
            payment_status='paid'
        ).aggregate(total=Sum('amount_total'))['total'] or 0
        
        total_revenue = booking_revenue + order_revenue
        
        # 2. Task Metrics (Pending Actions)
        pending_bookings = Booking.objects.filter(booking_status='pending').count()
        pending_orders = Order.objects.filter(status='created').count()
        
        # 3. Operations Metrics
        today_bookings = Booking.objects.filter(appointment_date=today).count()
        completed_today = Booking.objects.filter(
            appointment_date=today, 
            booking_status='completed'
        ).count()
        
        # 4. Inventory Health
        low_stock_count = SparePart.objects.filter(stock_qty__lt=5).count()
        out_of_stock_count = SparePart.objects.filter(stock_qty=0).count()
        
        latency = (time.time() - start_time) * 1000
        if latency > 500:
            logger.warning(f"Dashboard metrics aggregation slow: {latency:.2f}ms")
        
        return {
            'revenue': {
                'today': float(total_revenue),
                'bookings': float(booking_revenue),
                'orders': float(order_revenue),
            },
            'tasks': {
                'pending_bookings': pending_bookings,
                'pending_orders': pending_orders,
            },
            'today_view': {
                'total_bookings': today_bookings,
                'completed': completed_today,
                'progress_percent': round((completed_today / today_bookings * 100), 1) if today_bookings > 0 else 0.0
            },
            'inventory': {
                'low_stock': low_stock_count,
                'out_of_stock': out_of_stock_count
            }
        }
    except Exception as e:
        logger.error(f"Error calculating dashboard metrics: {e}")
        return {
            'revenue': {'today': 0, 'bookings': 0, 'orders': 0},
            'tasks': {'pending_bookings': 0, 'pending_orders': 0},
            'today_view': {'total_bookings': 0, 'completed': 0, 'progress_percent': 0},
            'inventory': {'low_stock': 0, 'out_of_stock': 0}
        }

def get_recent_activity(limit=10):
    """Combine bookings and orders into a single activity feed."""
    activity = []
    
    bookings = Booking.objects.select_related('customer').order_by('-created_at')[:limit]
    for b in bookings:
        activity.append({
            'type': 'booking',
            'id': b.id,
            'title': f"New Booking: {b.customer.name}",
            'subtitle': f"Slot: {b.appointment_date} {b.appointment_time}",
            'status': b.booking_status,
            'time': b.created_at
        })
        
    orders = Order.objects.order_by('-created_at')[:limit]
    for o in orders:
        activity.append({
            'type': 'order',
            'id': o.id,
            'title': f"Product Order: {o.customer_name}",
            'subtitle': f"Amount: ₹{o.amount_total}",
            'status': o.status,
            'time': o.created_at
        })
        
    # Sort by time descendings
    activity.sort(key=lambda x: x['time'], reverse=True)
    return activity[:limit]
