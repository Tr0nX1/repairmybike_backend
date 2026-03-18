from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Booking
from notifications.utils import notify_booking_status_changed


@receiver(pre_save, sender=Booking)
def capture_old_booking_status(sender, instance, **kwargs):
    if instance.id:
        try:
            instance._old_status = Booking.objects.get(id=instance.id).booking_status
        except Booking.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Booking)
def trigger_booking_notification(sender, instance, created, **kwargs):
    # Success cases: 
    # 1. New booking created (might want to notify admin, but typically we notify user on status transitions)
    # 2. Status changed from old status
    old_status = getattr(instance, '_old_status', None)
    
    if created:
        # For new bookings, we could notify but usually confirmed is the first big update
        pass
    elif old_status and old_status != instance.booking_status:
        notify_booking_status_changed(instance, old_status)


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
def notify_dashboard_new_booking(sender, instance, created, **kwargs):
    if created:
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'dashboard_notifications',
                {
                    'type': 'dashboard_message',
                    'message': f"New Booking: {instance.customer.name} (ID: #{instance.id})"
                }
            )
        except Exception:
            pass