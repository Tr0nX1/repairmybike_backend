from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import logging
from decimal import Decimal

from .models import CashSession
from staff.models import ActivityLog
from repairmybike.fcm import send_push_notification, send_push_to_multiple

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=CashSession)
def cache_previous_cash_session_status(sender, instance: CashSession, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    try:
        instance._previous_status = CashSession.objects.only('status').get(pk=instance.pk).status
    except CashSession.DoesNotExist:
        instance._previous_status = None

@receiver(post_save, sender=CashSession)
def cash_variance_push_notification(sender, instance, created, **kwargs):
    """
    Trigger 4: Cash Variance Flagged
    """
    old_status = getattr(instance, '_previous_status', None)
    if not created and old_status != instance.status and instance.status == 'pending_approval':
        def send_notifications():
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                superusers = User.objects.filter(is_superuser=True, is_active=True)
                variance = instance.variance or Decimal('0.00')
                staff_name = instance.staff.get_full_name() or instance.staff.username
                
                title = "Cash Variance Alert"
                body = f"{staff_name}'s session has ₹{variance} variance. Needs approval."
                data = {'type': 'cash_variance', 'session_id': str(instance.id)}
                
                send_push_to_multiple(superusers, title, body, data)
                
                # Log the notification
                ActivityLog.objects.create(
                    action_type='push_notification_sent',
                    description=f"Admins notified of cash variance for session #{instance.id}",
                    content_object=instance,
                    metadata={'notification_type': 'cash_variance', 'session_id': instance.id, 'variance': str(variance)}
                )
            except Exception as e:
                logger.error(f"Error in cash_variance_push_notification signal: {e}")

        transaction.on_commit(send_notifications)
