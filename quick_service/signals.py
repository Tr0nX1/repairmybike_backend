from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import QuickServiceRequest
from notifications.utils import notify_quick_service_update


@receiver(pre_save, sender=QuickServiceRequest)
def capture_old_qs_status(sender, instance, **kwargs):
    if instance.id:
        try:
            instance._old_status = QuickServiceRequest.objects.get(id=instance.id).status
        except QuickServiceRequest.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=QuickServiceRequest)
def trigger_qs_notification(sender, instance, created, **kwargs):
    old_status = getattr(instance, '_old_status', None)
    
    # Notify when status changes
    if not created and old_status != instance.status:
        notify_quick_service_update(instance)
