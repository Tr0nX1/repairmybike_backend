from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import logging

from .models import SparePart
from staff.models import ActivityLog
from repairmybike.fcm import send_push_to_multiple

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=SparePart)
def cache_previous_stock(sender, instance: SparePart, **kwargs):
    if not instance.pk:
        instance._previous_stock_qty = None
        return
    try:
        instance._previous_stock_qty = SparePart.objects.only('stock_qty').get(pk=instance.pk).stock_qty
    except SparePart.DoesNotExist:
        instance._previous_stock_qty = None

@receiver(post_save, sender=SparePart)
def low_stock_push_notification(sender, instance, created, **kwargs):
    """
    Trigger 5: Low Stock Alert
    """
    old_stock = getattr(instance, '_previous_stock_qty', None)
    new_stock = instance.stock_qty
    
    if old_stock != new_stock:
        # Check if we should notify
        notify = False
        title = ""
        body = ""
        
        if 0 < new_stock <= 5 and (old_stock is None or old_stock > 5):
            notify = True
            title = f"Low Stock: {instance.name}"
            body = f"Only {new_stock} units remaining."
        elif new_stock == 0 and (old_stock is None or old_stock > 0):
            notify = True
            title = f"OUT OF STOCK: {instance.name}"
            body = f"{instance.name} is now out of stock."
            
        if notify:
            def send_notifications():
                try:
                    from django.contrib.auth import get_user_model
                    from notifications.models import Notification
                    User = get_user_model()
                    
                    superusers = User.objects.filter(is_superuser=True, is_active=True)
                    data = {'type': 'low_stock', 'part_id': str(instance.id)}
                    
                    # Create Notification rows in DB for all superusers
                    for admin in superusers:
                        Notification.objects.create(
                            user=admin,
                            title=title,
                            message=body,
                            notification_type='system' # Or add 'stock_alert' if you want to extend choices
                        )
                    
                    success = send_push_to_multiple(superusers, title, body, data)
                    if success:
                        ActivityLog.objects.create(
                            action_type='push_notification_sent',
                            description=f"Admins notified of low stock: {instance.name}",
                            content_object=instance,
                            metadata={'notification_type': 'low_stock', 'part_id': instance.id, 'stock_qty': new_stock}
                        )
                except Exception as e:
                    logger.error(f"Error in low_stock_push_notification signal: {e}")

            transaction.on_commit(send_notifications)
