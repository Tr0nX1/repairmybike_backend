from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Order
from notifications.utils import notify_order_shipped


@receiver(pre_save, sender=Order)
def capture_old_order_status(sender, instance, **kwargs):
    if instance.id:
        try:
            instance._old_status = Order.objects.get(id=instance.id).status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Order)
def trigger_order_notification(sender, instance, created, **kwargs):
    old_status = getattr(instance, '_old_status', None)
    
    # Notify when status changes to fulfilled (shipped)
    if not created and old_status != instance.status and instance.status == 'fulfilled':
        notify_order_shipped(instance)


@receiver(post_save, sender=Order)
def notify_dashboard_new_order(sender, instance, created, **kwargs):
    if created:
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'dashboard_notifications',
                {
                    'type': 'dashboard_message',
                    'message': f"New Order: #{instance.id} - {instance.payment_status}"
                }
            )
        except Exception:
            pass
