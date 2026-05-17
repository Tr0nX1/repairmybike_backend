from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import logging

from spare_parts.models import SparePart
from staff.models import ActivityLog
from repairmybike.fcm import send_push_notification, send_push_to_multiple

from .models import Booking, BookingPart

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Booking)
def cache_previous_booking_status(sender, instance: Booking, **kwargs):
    if not instance.pk:
        instance._previous_booking_status = None
        return
    try:
        instance._previous_booking_status = Booking.objects.only('booking_status').get(pk=instance.pk).booking_status
    except Booking.DoesNotExist:
        instance._previous_booking_status = None


@receiver(post_save, sender=Booking)
def booking_push_notifications(sender, instance, created, **kwargs):
    """
    Handle push notifications for Booking lifecycle:
    1. New booking (Notify staff)
    2. Status changed (Notify customer)
    """
    def send_notifications():
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            if created:
                # Trigger 1: New Booking
                staff_users = User.objects.filter(is_staff=True, is_active=True)
                title = f"New Booking #{instance.id}"
                body = f"New booking for {instance.appointment_date}. Tap to view."
                data = {'type': 'new_booking', 'booking_id': str(instance.id)}
                
                send_push_to_multiple(staff_users, title, body, data)
                # Note: We'll skip logging ActivityLog here to avoid recursive signal loops or noise unless requested
            else:
                # Trigger 2: Status Change
                old_status = getattr(instance, '_previous_booking_status', None)
                if old_status != instance.booking_status:
                    status_messages = {
                        'confirmed': f"Your booking is confirmed! We'll see you on {instance.appointment_date}.",
                        'in_progress': f"Work has started on your vehicle. 🔧",
                        'completed': "Your bike is ready for pickup! 🎉",
                        'cancelled': f"Your booking #{instance.id} has been cancelled."
                    }
                    
                    if instance.booking_status in status_messages:
                        user = User.objects.filter(phone_number=instance.customer.phone).first()
                        if user:
                            title = "Booking Update"
                            body = status_messages[instance.booking_status]
                            data = {'type': 'booking_status', 'booking_id': str(instance.id), 'status': instance.booking_status}
                            
                            send_push_notification(user, title, body, data)

        except Exception as e:
            logger.error(f"Error in booking_push_notifications signal: {e}")

    transaction.on_commit(send_notifications)


@receiver(post_save, sender=BookingPart)
def booking_part_push_notifications(sender, instance, created, **kwargs):
    """
    Trigger 3: Parts Added (Notify customer for approval)
    """
    if created:
        def send_notifications():
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                booking = instance.booking
                user = User.objects.filter(phone_number=booking.customer.phone).first()
                
                if user:
                    title = "Parts Added to Your Repair"
                    body = f"A new part was added: {instance.spare_part.name} (₹{instance.unit_price}). Tap to approve."
                    data = {'type': 'parts_approval', 'booking_id': str(booking.id), 'part_id': str(instance.id)}
                    
                    send_push_notification(user, title, body, data)
            except Exception as e:
                logger.error(f"Error in booking_part_push_notifications signal: {e}")

        transaction.on_commit(send_notifications)


@receiver(post_save, sender=Booking)
def consume_subscription_visit_on_completion(sender, instance: Booking, created, **kwargs):
    # Only act when booking exists and is marked completed
    if not instance.subscription:
        return
    if instance.booking_status != 'completed':
        return
    # Prevent double counting
    if instance.subscription_visit_consumed:
        return

    subscription = instance.subscription
    try:
        included = subscription.plan.included_visits or 0
        consumed = subscription.visits_consumed or 0
        if consumed < included:
            subscription.visits_consumed = consumed + 1
            subscription.save(update_fields=["visits_consumed", "updated_at"])
            # Mark booking as counted
            instance.subscription_visit_consumed = True
            instance.save(update_fields=["subscription_visit_consumed", "updated_at"])
    except Exception:
        # Silently ignore; do not block booking save
        pass


@receiver(post_save, sender=Booking)
def deduct_approved_part_stock_on_completion(sender, instance: Booking, created, **kwargs):
    if created:
        return
    if instance.booking_status != 'completed':
        return
    if getattr(instance, '_previous_booking_status', None) == 'completed':
        return
    if instance.stock_deducted:
        return

    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=instance.pk)
        if booking.booking_status != 'completed' or booking.stock_deducted:
            return

        approved_parts = BookingPart.objects.select_related('spare_part').filter(
            booking=booking,
            approval_status=BookingPart.APPROVAL_APPROVED,
        )
        for booking_part in approved_parts:
            part = SparePart.objects.select_for_update().get(id=booking_part.spare_part_id)
            if part.stock_qty < booking_part.quantity:
                raise ValueError(
                    f"Insufficient stock for {part.name}. "
                    f"Available: {part.stock_qty}, required: {booking_part.quantity}"
                )
            part.stock_qty -= booking_part.quantity
            part.in_stock = part.stock_qty > 0
            part.save(update_fields=['stock_qty', 'in_stock', 'updated_at'])

            ActivityLog.objects.create(
                user=None,
                action_type='stock_deducted',
                description=f"Deducted {booking_part.quantity}x {part.name} for Booking #{booking.id}",
                content_object=booking_part,
                metadata={
                    'old_value': part.stock_qty + booking_part.quantity,
                    'new_value': part.stock_qty,
                    'booking_id': booking.id,
                    'booking_part_id': booking_part.id,
                    'part_id': part.id,
                    'quantity': booking_part.quantity,
                    'amount': str(booking_part.total_price),
                    'stock_qty': part.stock_qty,
                }
            )

        booking.stock_deducted = True
        booking.save(update_fields=['stock_deducted', 'updated_at'])
