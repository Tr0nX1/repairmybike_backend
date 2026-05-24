from django.db import models
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Subscription

@receiver(post_save, sender=Subscription)
def notify_staff_on_subscription_request(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.status != 'pending':
        return
    
    def send_notifications():
        try:
            from django.contrib.auth import get_user_model
            from notifications.models import Notification
            from staff.models import ActivityLog
            User = get_user_model()
            
            # Notify all active staff and managers
            staff_users = User.objects.filter(
                is_active=True
            ).filter(
                models.Q(is_staff=True) | 
                models.Q(is_manager=True) | 
                models.Q(is_superuser=True)
            ).distinct()
            
            plan_name = instance.plan.name
            user_name = getattr(instance.user, 'username', 'A customer')
            
            title = "New Subscription Request"
            body = f"{user_name} has requested the {plan_name} plan."
            data = {
                'type': 'subscription_request',
                'subscription_id': str(instance.id),
                'plan_name': plan_name,
            }
            
            # Create Notification rows
            for staff in staff_users:
                Notification.objects.create(
                    user=staff,
                    title=title,
                    message=body,
                    notification_type='subscription'
                )
            
            # Send push notifications
            from repairmybike.fcm import send_push_to_multiple
            send_push_to_multiple(staff_users, title, body, data)
            
            # ActivityLog
            ActivityLog.objects.create(
                user=instance.user,
                action_type='subscription_requested',
                description=f"Subscription requested for plan: {plan_name}",
                content_object=instance,
                metadata={
                    'subscription_id': str(instance.id),
                    'plan_id': str(instance.plan.id),
                    'plan_name': plan_name,
                }
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                f"Failed to notify staff of subscription request: {e}"
            )
    
    transaction.on_commit(send_notifications)
