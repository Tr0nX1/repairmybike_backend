from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Subscription


@receiver(post_save, sender=Subscription)
def notify_dashboard_new_subscription(sender, instance, created, **kwargs):
    if created:
        try:
            channel_layer = get_channel_layer()
            user_identifier = instance.contact_phone or (instance.user.phone_number if instance.user else "Unknown")
            
            async_to_sync(channel_layer.group_send)(
                'dashboard_notifications',
                {
                    'type': 'dashboard_message',
                    'message': f"New Subscription: {instance.plan.name} for {user_identifier} ({instance.status})"
                }
            )
        except Exception:
            pass
