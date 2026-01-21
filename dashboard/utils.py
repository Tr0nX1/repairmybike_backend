import logging
import time
from django.utils import timezone
from django.db.models import Sum, Q, Count
from bookings.models import Booking
from spare_parts.models import Order, SparePart

logger = logging.getLogger(__name__)

def get_dashboard_metrics():
    start_time = time.time()
    today = timezone.now().date()
    
    try:
        # 1. Booking Metrics (1 Query)
        booking_metrics = Booking.objects.filter(
            Q(appointment_date=today) | Q(booking_status='pending')
        ).aggregate(
            today_total=Count('id', filter=Q(appointment_date=today)),
            today_completed=Count('id', filter=Q(appointment_date=today, booking_status='completed')),
            revenue_today=Sum('total_amount', filter=Q(appointment_date=today, payment_status='completed')),
            pending_count=Count('id', filter=Q(booking_status='pending'))
        )
        
        # 2. Order Metrics (1 Query)
        order_metrics = Order.objects.filter(
            Q(created_at__date=today) | Q(status='created')
        ).aggregate(
            revenue_today=Sum('amount_total', filter=Q(created_at__date=today, payment_status='paid')),
            pending_dispatch=Count('id', filter=Q(status='created'))
        )
        
        # 3. Inventory Metrics (1 Query)
        inventory_metrics = SparePart.objects.aggregate(
            low_stock=Count('id', filter=Q(stock_qty__lt=5)),
            out_of_stock=Count('id', filter=Q(stock_qty=0))
        )

        booking_rev = float(booking_metrics['revenue_today'] or 0)
        order_rev = float(order_metrics['revenue_today'] or 0)
        total_revenue = booking_rev + order_rev
        
        today_total = booking_metrics['today_total']
        today_completed = booking_metrics['today_completed']
        
        latency = (time.time() - start_time) * 1000
        if latency > 500:
            logger.warning(f"Dashboard metrics aggregation slow: {latency:.2f}ms")
        
        return {
            'revenue': {
                'today': total_revenue,
                'bookings': booking_rev,
                'orders': order_rev,
            },
            'tasks': {
                'pending_bookings': booking_metrics['pending_count'],
                'pending_orders': order_metrics['pending_dispatch'],
            },
            'today_view': {
                'total_bookings': today_total,
                'completed': today_completed,
                'progress_percent': round((today_completed / today_total * 100), 1) if today_total > 0 else 0.0
            },
            'inventory': {
                'low_stock': inventory_metrics['low_stock'],
                'out_of_stock': inventory_metrics['out_of_stock']
            }
        }
    except Exception as e:
        logger.error(f"Error calculating dashboard metrics: {e}")
        return {
            'revenue': {'today': 0.0, 'bookings': 0.0, 'orders': 0.0},
            'tasks': {'pending_bookings': 0, 'pending_orders': 0},
            'today_view': {'total_bookings': 0, 'completed': 0, 'progress_percent': 0.0},
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
