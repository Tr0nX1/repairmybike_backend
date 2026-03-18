import os
import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
from .models import FCMDevice, NotificationLog

logger = logging.getLogger(__name__)

def init_firebase_app():
    """Initialize Firebase Admin SDK"""
    if not firebase_admin._apps:
        cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', 'firebase_credentials.json')
        
        # Check if the file exists
        if not os.path.exists(cred_path):
            logger.error(f"Firebase credentials file not found at {cred_path}. Push notifications will not work.")
            return False

        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully.")
            return True
        except Exception as e:
            logger.exception(f"Failed to initialize Firebase Admin SDK: {e}")
            return False
    return True

def send_push(user, title, body, data=None):
    """
    Send a push notification to all active devices of a user.
    """
    if data is None:
        data = {}
    
    # Cast all values in data to strings for FCM
    data = {k: str(v) for k, v in data.items()}

    devices = FCMDevice.objects.filter(user=user, is_active=True)
    if not devices.exists():
        logger.info(f"No active devices found for user {user.username}")
        return []

    tokens = list(devices.values_list('token', flat=True))
    
    # Prepare messages
    messages = [
        messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data,
            token=token,
        ) for token in tokens
    ]

    try:
        # Send notifications
        response = messaging.send_each(messages)
        
        # Log the notification
        log_entry = NotificationLog.objects.create(
            user=user,
            title=title,
            body=body,
            data=data,
            fcm_response={
                'success_count': response.success_count,
                'failure_count': response.failure_count,
            }
        )

        # Handle failed tokens (e.g., unregistered)
        for i, send_response in enumerate(response.responses):
            if not send_response.success:
                error = send_response.exception
                if isinstance(error, messaging.UnregisteredError):
                    # Deactivate stale token
                    failed_token = tokens[i]
                    FCMDevice.objects.filter(token=failed_token).update(is_active=False)
                    logger.info(f"Deactivated stale FCM token for user {user.username}")

        return response
    except Exception as e:
        logger.exception(f"Error sending push notifications: {e}")
        return None

# Business-specific notification helpers

def notify_booking_status_changed(booking, old_status):
    """Notify customer when booking status changes"""
    user = booking.customer.user # Assuming Customer model has a link to User, or we find user by phone
    # Actually, looking at bookings/models.py, Customer is a standalone model.
    # But in authentication/models.py, User has a phone_number.
    # Let's try to find the user by phone.
    from authentication.models import User
    try:
        user = User.objects.get(phone_number=booking.customer.phone)
    except User.DoesNotExist:
        logger.warning(f"No User found for phone {booking.customer.phone}. Cannot send push.")
        return

    status_name = booking.booking_status.replace('_', ' ').title()
    title = f"Booking {status_name} ✅"
    body = f"Your booking for {booking.vehicle_model.name} is now {status_name}."
    
    if booking.booking_status == 'confirmed':
        body = f"Great news! Your booking for {booking.vehicle_model.name} has been confirmed for {booking.appointment_date}."
    elif booking.booking_status == 'completed':
        title = "Service Completed! 🏁"
        body = f"Your service for {booking.vehicle_model.name} is complete. Hope you're happy with our work!"

    send_push(user, title, body, {
        'type': 'booking_update',
        'booking_id': booking.id,
        'status': booking.booking_status
    })

def notify_quick_service_update(qs_request):
    """Notify user about Quick Service status changes"""
    user = qs_request.user
    status_name = qs_request.status.replace('_', ' ').title()
    title = f"Quick Service Update: {status_name}"
    body = f"Your quick service request is now {status_name}."

    if qs_request.status == 'mechanic_dispatched':
        body = "A mechanic has been dispatched to your location! 🛵"
    
    send_push(user, title, body, {
        'type': 'quick_service_update',
        'request_id': qs_request.id,
        'status': qs_request.status
    })

def notify_order_shipped(order):
    """Notify user when spare part order is shipped"""
    if not order.user:
        return
        
    title = "Order Shipped! 📦"
    body = f"Your order #{order.id} for spare parts has been shipped."
    if order.courier_name and order.tracking_number:
        body += f" via {order.courier_name}. Tracking: {order.tracking_number}"

    send_push(order.user, title, body, {
        'type': 'order_update',
        'order_id': order.id,
        'status': 'shipped'
    })
