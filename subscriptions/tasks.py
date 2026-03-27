"""
Subscription renewal tasks — run periodically via APScheduler or management command.
"""
import logging
from django.utils import timezone
from django.db import transaction

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='subscriptions.tasks.process_subscription_renewals_task')
def process_subscription_renewals_task():
    """Celery wrapper for the renewal logic"""
    return process_subscription_renewals()


def process_subscription_renewals():
    """
    Process all subscriptions due for renewal.
    - auto_renew=True + active + next_billing_date <= now() → renew
    - auto_renew=False + end_date <= now() → expire
    
    Returns a summary dict.
    """
    from .models import Subscription

    now = timezone.now()
    renewed = 0
    expired = 0
    errors = []

    # 1. Renew subscriptions with auto_renew=True
    due_for_renewal = Subscription.objects.filter(
        auto_renew=True,
        status='active',
        next_billing_date__lte=now,
    ).select_related('plan', 'user')

    for sub in due_for_renewal:
        try:
            with transaction.atomic():
                success = sub.renew()
                if success:
                    renewed += 1
                    logger.info(
                        f"Renewed subscription #{sub.id} ({sub.plan.name}) "
                        f"for user {sub.user_id or sub.contact_phone}"
                    )
                    # Send renewal notification
                    _notify_renewal(sub)
        except Exception as e:
            errors.append({'subscription_id': sub.id, 'error': str(e)})
            logger.error(f"Failed to renew subscription #{sub.id}: {e}")

    # 2. Expire subscriptions that are past end date and not auto-renewing
    expired_subs = Subscription.objects.filter(
        status='active',
        auto_renew=False,
        end_date__lte=now,
    ).select_related('plan', 'user')

    for sub in expired_subs:
        try:
            sub.status = 'expired'
            sub.save(update_fields=['status', 'updated_at'])
            expired += 1
            logger.info(
                f"Expired subscription #{sub.id} ({sub.plan.name}) "
                f"for user {sub.user_id or sub.contact_phone}"
            )
            # Send expiry notification
            _notify_expiry(sub)
        except Exception as e:
            errors.append({'subscription_id': sub.id, 'error': str(e)})
            logger.error(f"Failed to expire subscription #{sub.id}: {e}")

    # 3. Send upcoming renewal reminders (3 days before)
    reminder_window = now + timezone.timedelta(days=3)
    upcoming = Subscription.objects.filter(
        auto_renew=True,
        status='active',
        next_billing_date__gt=now,
        next_billing_date__lte=reminder_window,
    ).exclude(
        metadata__has_key='renewal_reminder_sent'
    ).select_related('plan', 'user')

    reminders_sent = 0
    for sub in upcoming:
        try:
            _notify_upcoming_renewal(sub)
            # Mark reminder sent to avoid duplicates
            if not isinstance(sub.metadata, dict):
                sub.metadata = {}
            sub.metadata['renewal_reminder_sent'] = now.isoformat()
            sub.save(update_fields=['metadata', 'updated_at'])
            reminders_sent += 1
        except Exception as e:
            logger.error(f"Failed to send renewal reminder for #{sub.id}: {e}")

    summary = {
        'timestamp': now.isoformat(),
        'renewed': renewed,
        'expired': expired,
        'reminders_sent': reminders_sent,
        'errors': errors,
    }
    logger.info(f"Subscription renewal task completed: {summary}")
    return summary


def _notify_renewal(subscription):
    """Send push + email notification for a successful renewal."""
    from notifications.utils import send_push_notification, EmailService

    if subscription.user:
        send_push_notification(
            subscription.user,
            "Subscription Renewed",
            f"Your {subscription.plan.name} subscription has been renewed! "
            f"Valid until {subscription.end_date.strftime('%d %b %Y')}.",
            data={'type': 'subscription', 'subscription_id': str(subscription.id)}
        )


def _notify_expiry(subscription):
    """Send push notification for an expired subscription."""
    from notifications.utils import send_push_notification

    if subscription.user:
        send_push_notification(
            subscription.user,
            "Subscription Expired",
            f"Your {subscription.plan.name} subscription has expired. "
            f"Renew now to continue enjoying your benefits!",
            data={'type': 'subscription', 'subscription_id': str(subscription.id)}
        )


def _notify_upcoming_renewal(subscription):
    """Send reminder for upcoming renewal (3 days before)."""
    from notifications.utils import send_push_notification

    if subscription.user:
        days_left = (subscription.next_billing_date - timezone.now()).days
        send_push_notification(
            subscription.user,
            "Renewal Reminder",
            f"Your {subscription.plan.name} subscription renews in {days_left} day(s). "
            f"Amount: ₹{subscription.plan.discount_price or subscription.plan.price}",
            data={'type': 'subscription', 'subscription_id': str(subscription.id)}
        )
