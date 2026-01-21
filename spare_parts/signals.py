from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Order


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
