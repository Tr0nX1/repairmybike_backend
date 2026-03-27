import logging
from django.db import models
from celery import shared_task
from .utils import send_push_notification, EmailService

logger = logging.getLogger(__name__)

@shared_task(name='notifications.tasks.send_push_notification_task')
def send_push_notification_task(user_id, title, body, data=None):
    """
    Asynchronous task to send push notification.
    """
    from authentication.models import User
    try:
        user = User.objects.get(id=user_id)
        return send_push_notification(user, title, body, data)
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found for push notification.")
        return False
    except Exception as e:
        logger.error(f"Error in send_push_notification_task: {e}")
        return False

@shared_task(name='notifications.tasks.send_email_task')
def send_email_task(subject, template_name, context, recipient_list):
    """
    Asynchronous task to send HTML emails.
    """
    try:
        return EmailService.send_html_email(subject, template_name, context, recipient_list)
    except Exception as e:
        logger.error(f"Error in send_email_task: {e}")
        return False

@shared_task(name='notifications.tasks.notify_booking_status_task')
def notify_booking_status_task(booking_id, old_status=None):
    """
    Asynchronous task to notify booking status changes.
    """
    from bookings.models import Booking
    from .utils import notify_booking_status_changed, notify_booking_confirmed
    
    try:
        booking = Booking.objects.get(id=booking_id)
        if old_status:
            return notify_booking_status_changed(booking, old_status)
        else:
            return notify_booking_confirmed(booking)
    except Booking.DoesNotExist:
        logger.error(f"Booking with ID {booking_id} not found for status notification.")
        return False
    except Exception as e:
        logger.error(f"Error in notify_booking_status_task: {e}")
        return False

@shared_task(name='notifications.tasks.send_periodic_service_reminders')
def send_periodic_service_reminders():
    """
    Find vehicles where the last service was > 6 months ago 
    and send a reminder notification.
    """
    from django.utils import timezone
    from datetime import timedelta
    from vehicles.models import UserVehicle
    
    # 6 months threshold
    threshold_date = timezone.now().date() - timedelta(days=180)
    
    # Simple logic: last_service_date is before threshold 
    # OR (never serviced AND created before threshold)
    due_vehicles = UserVehicle.objects.filter(
        models.Q(last_service_date__lte=threshold_date) |
        models.Q(last_service_date__isnull=True, created_at__date__lte=threshold_date)
    ).select_related('user', 'vehicle_model__vehicle_brand')
    
    count = 0
    for vehicle in due_vehicles:
        title = "Service Due Reminder 🚲"
        body = f"Your {vehicle.vehicle_model.vehicle_brand.name} {vehicle.vehicle_model.name} is due for a checkup! It's been over 6 months since your last service."
        
        # Send push
        if send_push_notification(vehicle.user, title, body, data={'type': 'service_reminder', 'vehicle_id': str(vehicle.id)}):
            count += 1
            
    logger.info(f"Sent {count} periodic service reminders.")
    return count
