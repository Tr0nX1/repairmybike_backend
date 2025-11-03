from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Booking


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