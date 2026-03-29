import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import os
from .whatsapp import send_whatsapp_message

logger = logging.getLogger(__name__)

def init_firebase_app():
    """
    Initialize Firebase Admin SDK
    """
    if not firebase_admin._apps:
        cred_path = settings.FIREBASE_CREDENTIALS_PATH
        if os.path.exists(cred_path):
            try:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully.")
            except Exception as e:
                logger.error(f"Error initializing Firebase Admin SDK: {e}")
        else:
            logger.warning(f"Firebase credentials not found at {cred_path}. Push notifications disabled.")

def send_push_notification(user, title, body, data=None):
    """
    Send push notification to all active devices of a user.
    """
    from .models import FCMDevice, NotificationLog
    
    devices = FCMDevice.objects.filter(user=user, is_active=True)
    if not devices.exists():
        logger.info(f"No active FCM devices found for user {user}")
        return False

    tokens = list(devices.values_list('token', flat=True))
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        tokens=tokens,
    )

    try:
        response = messaging.send_each_for_multicast(message)
        # Log the notification
        NotificationLog.objects.create(
            user=user,
            title=title,
            body=body,
            data=data or {},
            fcm_response={
                'success_count': response.success_count,
                'failure_count': response.failure_count,
            }
        )
        logger.info(f"Sent push notification: {title} to {response.success_count} devices.")
        return True
    except Exception as e:
        logger.error(f"Error sending push notification: {e}")
        return False

def _get_user_for_customer(customer):
    """
    Helper to find the Django User for a Customer based on phone number.
    """
    from authentication.models import User
    return User.objects.filter(phone_number=customer.phone).first()

def notify_booking_status_changed(booking, old_status):
    """
    Trigger notification when booking status changes.
    """
    status_messages = {
        'confirmed': ("Booking Confirmed", "Your booking #{} has been confirmed!"),
        'in_progress': ("Service Started", "Our technician has started working on your booking #{}."),
        'completed': ("Service Completed", "Success! Your booking #{} is now complete."),
        'cancelled': ("Booking Cancelled", "Your booking #{} has been cancelled."),
    }

    if booking.booking_status in status_messages:
        title, body_tmpl = status_messages[booking.booking_status]
        body = body_tmpl.format(booking.id)
        user = _get_user_for_customer(booking.customer)
        if user:
            send_push_notification(user, title, body, data={'booking_id': str(booking.id), 'type': 'booking'})
            
        # Also send via WhatsApp
        send_whatsapp_message(user, booking.customer.phone, body)

def notify_booking_confirmed(booking):
    """
    Notify user when a booking is initially confirmed.
    """
    user = _get_user_for_customer(booking.customer)
    if user:
        title = "Booking Confirmed"
        body = f"Your booking #{booking.id} is confirmed for {booking.appointment_date.strftime('%d %b')}."
        send_push_notification(user, title, body, data={'booking_id': str(booking.id), 'type': 'booking'})
        
        # Also send via WhatsApp
        send_whatsapp_message(user, booking.customer.phone, body)

def notify_payment_received(payment):
    """
    Notify user when a payment is successfully received.
    """
    booking = payment.booking
    user = _get_user_for_customer(booking.customer)
    if user:
        title = "Payment Received"
        body = f"We've received ₹{payment.amount} for your booking #{booking.id}."
        send_push_notification(user, title, body, data={'booking_id': str(booking.id), 'type': 'payment'})

def notify_order_shipped(order):
    """
    Notify user when an order is shipped.
    """
    if order.user:
        title = "Order Shipped"
        body = f"Your order #{order.id} for spare parts has been shipped!"
        send_push_notification(order.user, title, body, data={'order_id': str(order.id), 'type': 'order'})
        
        # Also send via WhatsApp (if phone exists)
        phone = order.user.phone_number if hasattr(order.user, 'phone_number') else None
        if phone:
            send_whatsapp_message(order.user, phone, body)

def notify_order_status_update(order):
    """
    Notify user of spare part order status changes.
    """
    status_messages = {
        'shipped': ("Order Shipped", "Your order #{} has been shipped! Tracking: {}"),
        'out_for_delivery': ("Out for Delivery", "Your order #{} is out for delivery!"),
        'delivered': ("Order Delivered", "Your order #{} has been delivered successfully."),
        'cancelled': ("Order Cancelled", "Your order #{} has been cancelled."),
        'returned': ("Order Returned", "We've received the returned items for order #{}."),
    }

    if order.status in status_messages and order.user:
        title, body_tmpl = status_messages[order.status]
        if order.status == 'shipped' and order.tracking_number:
            body = body_tmpl.format(order.id, order.tracking_number)
        else:
            body = body_tmpl.format(order.id)
            
        send_push_notification(order.user, title, body, data={'order_id': str(order.id), 'type': 'order'})

def notify_mechanic_assigned(booking):
    """
    Notify customer that a mechanic has been assigned to their booking.
    """
    staff = booking.assigned_staff
    if not staff:
        return
        
    title = "Mechanic Assigned"
    body = f"Hi {booking.customer.name}, {staff.name} has been assigned to your booking #{booking.id}."
    
    # Send push to user if linked
    from authentication.models import User
    user = User.objects.filter(phone_number=booking.customer.phone).first()
    if user:
        send_push_notification(user, title, body, data={'booking_id': str(booking.id), 'type': 'booking'})
    
    # Send WhatsApp/SMS
    send_whatsapp_message(user, booking.customer.phone, body)

def notify_booking_status_update(booking):
    """
    Notify customer of booking status changes.
    """
    status_msg = {
        'confirmed': ("Booking Confirmed", f"Your booking #{booking.id} is confirmed for {booking.appointment_date}."),
        'assigned': ("Mechanic Assigned", f"A mechanic has been assigned to your booking #{booking.id}."),
        'in_progress': ("Service Started", f"The service for booking #{booking.id} is now in progress."),
        'completed': ("Service Completed", f"Great news! Your service for booking #{booking.id} is completed."),
        'cancelled': ("Booking Cancelled", f"Your booking #{booking.id} has been cancelled."),
    }
    
    if booking.booking_status in status_msg:
        title, body = status_msg[booking.booking_status]
        
        from authentication.models import User
        user = User.objects.filter(phone_number=booking.customer.phone).first()
        if user:
            send_push_notification(user, title, body, data={'booking_id': str(booking.id), 'type': 'booking'})

def notify_quick_service_update(qs_request):
    """
    Notify user of updates to a quick service request.
    """
    from authentication.models import User
    user = User.objects.filter(phone_number=qs_request.phone).first()
    if user:
        title = "Quick Service Update"
        body = f"Your quick service request #{qs_request.id} is now {qs_request.get_status_display()}."
        send_push_notification(user, title, body, data={'qs_id': str(qs_request.id), 'type': 'quick_service'})

class EmailService:
    @staticmethod
    def send_html_email(subject, template_name, context, recipient_list):
        """
        Base method to send HTML emails with a text fallback.
        """
        try:
            html_content = render_to_string(template_name, context)
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipient_list
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
            logger.info(f"Email sent successfully: {subject} to {recipient_list}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False

    @classmethod
    def send_booking_confirmation(cls, booking):
        """
        Send confirmation email for a new booking.
        """
        context = {
            'customer_name': booking.customer.name,
            'booking_id': booking.id,
            'service_type': booking.get_service_location_display(),
            'vehicle_model': f"{booking.vehicle_model.vehicle_brand.name} {booking.vehicle_model.name}",
            'appointment_date': booking.appointment_date.strftime('%d %b %Y'),
            'appointment_time': booking.appointment_time.strftime('%I:%M %p'),
            'service_location': booking.address,
        }
        return cls.send_html_email(
            subject=f"Booking Confirmed: #{booking.id} - RepairMyBike",
            template_name='emails/booking_confirmation.html',
            context=context,
            recipient_list=[booking.customer.email]
        )

    @classmethod
    def send_order_confirmation(cls, order):
        """
        Send confirmation email for a spare parts order.
        Gracefully skips if no valid recipient email is available.
        """
        # Guard: do not attempt send if there is no valid email address
        # order.user may be None (guest) or user.email may be blank/None
        recipient = None
        if order.user and order.user.email and order.user.email.strip():
            recipient = order.user.email.strip()
        
        # Fallback: try the phone-based lookup won't help for email,
        # so skip silently rather than crash
        if not recipient:
            logger.info(f"Skipping order confirmation email for order #{order.id}: no valid recipient email.")
            return False

        try:
            items = [
                {'name': item.spare_part.name, 'quantity': item.quantity, 'price': item.unit_price}
                for item in order.items.all()
            ]
            context = {
                'customer_name': order.customer_name,
                'order_id': order.id,
                'items': items,
                'total_amount': order.amount_total,
                'shipping_address': order.address,
                'estimated_delivery': '3-5 Business Days',
            }
            return cls.send_html_email(
                subject=f"Order Confirmed: #{order.id} - RepairMyBike Parts",
                template_name='emails/order_confirmation.html',
                context=context,
                recipient_list=[recipient]
            )
        except Exception as e:
            logger.error(f"Failed to build order confirmation email for order #{order.id}: {e}")
            return False

    @classmethod
    def send_payment_receipt(cls, payment):
        """
        Send receipt for a successful payment.
        """
        booking = payment.booking
        context = {
            'customer_name': booking.customer.name,
            'booking_id': booking.id,
            'amount': payment.amount,
            'razorpay_payment_id': payment.razorpay_payment_id,
            'razorpay_order_id': payment.razorpay_order_id,
            'timestamp': payment.updated_at.strftime('%d %b %Y, %I:%M %p'),
        }
        return cls.send_html_email(
            subject=f"Payment Receipt: Booking #{booking.id}",
            template_name='emails/payment_receipt.html',
            context=context,
            recipient_list=[booking.customer.email]
        )

    @classmethod
    def send_invoice(cls, booking):
        """
        Send final tax invoice for a completed booking.
        """
        services = [
            {'name': bs.service.name, 'price': bs.price}
            for bs in booking.booking_services.all()
        ]
        context = {
            'customer_name': booking.customer.name,
            'booking_id': booking.id,
            'services': services,
            'subtotal': booking.total_amount,
            'total_amount': booking.total_amount,
            'payment_status': booking.payment_status,
            'vehicle_model': f"{booking.vehicle_model.vehicle_brand.name} {booking.vehicle_model.name}",
            'date': booking.appointment_date.strftime('%d %b %Y'),
            'timestamp_suffix': booking.updated_at.strftime('%H%M'),
        }
        return cls.send_html_email(
            subject=f"Tax Invoice: Booking #{booking.id} - RepairMyBike",
            template_name='emails/digital_invoice.html',
            context=context,
            recipient_list=[booking.customer.email]
        )
