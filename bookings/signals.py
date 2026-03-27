from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from django.db import transaction
from decimal import Decimal
from .models import Booking
from notifications.tasks import notify_booking_status_task, send_push_notification_task


@receiver(pre_save, sender=Booking)
def capture_old_booking_status(sender, instance, **kwargs):
    if instance.id:
        try:
            # Safely fetch the old status without triggering recursion
            instance._old_status = Booking.objects.only('booking_status').get(id=instance.id).booking_status
        except Booking.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Booking)
def trigger_booking_notification(sender, instance, created, **kwargs):
    # Delayed push notification via Celery to avoid blocking
    old_status = getattr(instance, '_old_status', None)
    
    if created:
        notify_booking_status_task.delay(instance.id)
    elif old_status and old_status != instance.booking_status:
        notify_booking_status_task.delay(instance.id, old_status)


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

@receiver(post_save, sender=Booking)
def award_loyalty_points_on_completion(sender, instance: Booking, created, **kwargs):
    """Award 1 point for every 100 spent on completed bookings."""
    if instance.booking_status != 'completed':
        return
    
    # Avoid duplicate awarding if completion happens multiple times
    if getattr(instance, '_old_status', None) == 'completed':
        return

    
    # Find the linked user via phone number
    user = User.objects.filter(phone_number=instance.customer.phone).first()
    if not user:
        return
    
    # Calculate points (1 point per 100 INR spent)
    points_to_award = int(instance.total_amount / Decimal('100'))
    if points_to_award <= 0:
        return
        
    with transaction.atomic():
        # Record transaction
        LoyaltyTransaction.objects.create(
            user=user,
            points=points_to_award,
            transaction_type='earned',
            description=f"Points earned for Booking #{instance.id}",
            booking=instance
        )
        
        # Update user balance and LTV
        user.loyalty_points += points_to_award
        user.total_ltv += instance.total_amount
        user.save(update_fields=['loyalty_points', 'total_ltv', 'updated_at'])
        
        # Send push notification about points earned
        send_push_notification_task.delay(
            user.id,
            "Rewards Points Earned! 🪙",
            f"You've earned {points_to_award} points for your recent service. Total balance: {user.loyalty_points}."
        )

@receiver(post_save, sender=Booking)
def award_referral_bonus_on_first_completion(sender, instance: Booking, created, **kwargs):
    """Award ₹500 (500 points) to the referrer when the referred user completes their first booking."""
    if instance.booking_status != 'completed':
        return
    
    # Avoid duplicate awarding
    if getattr(instance, '_old_status', None) == 'completed':
        return

    
    # Find the linked user
    user = User.objects.filter(phone_number=instance.customer.phone).first()
    if not user or not user.referred_by:
        return
    
    # Check if this is their first completed booking
    completed_count = Booking.objects.filter(
        customer__phone=user.phone_number,
        booking_status='completed'
    ).count()
    
    # If this is the first (it was just marked completed, so count should be 1)
    if completed_count == 1:
        referrer = user.referred_by
        bonus_points = 500 # ₹500 reward
        
        with transaction.atomic():
            # Record transaction for referrer
            LoyaltyTransaction.objects.create(
                user=referrer,
                points=bonus_points,
                transaction_type='earned',
                description=f"Referral bonus for {user.phone_number}'s first service",
                booking=instance
            )
            
            # Update referrer balance
            referrer.loyalty_points += bonus_points
            referrer.save(update_fields=['loyalty_points', 'updated_at'])
            
            # Notify referrer
            send_push_notification_task.delay(
                referrer.id,
                "Referral Reward! 🎁",
                f"You've earned {bonus_points} points because your friend completed their first service. Total balance: {referrer.loyalty_points}."
            )