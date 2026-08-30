import logging
from django.db import transaction
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from notifications.models import Notification
from repairmybike.fcm import send_push_to_multiple
from .models import QuickServiceRequest

logger = logging.getLogger(__name__)

User = get_user_model()


@receiver(post_save, sender=QuickServiceRequest)
def quick_service_request_notifications(sender, instance: QuickServiceRequest, created: bool, **kwargs):
    """
    Automatically notify all staff members when a new Quick Service request is created (status='initiated').
    Does not trigger on subsequent updates to existing requests.
    """
    if not created or instance.status != 'initiated':
        return

    def send_staff_notifications():
        try:
            # Query all active staff, manager, or superuser accounts
            staff_users = User.objects.filter(
                Q(is_staff=True) | Q(is_superuser=True) | Q(is_manager=True),
                is_active=True
            ).distinct()

            if not staff_users.exists():
                logger.info("No active staff users found to notify for QuickServiceRequest #%s", instance.id)
                return

            vehicle_parts = []
            if instance.vehicle_manufacturer:
                vehicle_parts.append(instance.vehicle_manufacturer)
            if instance.vehicle_model:
                vehicle_parts.append(instance.vehicle_model)
            if instance.vehicle_number:
                vehicle_parts.append(f"({instance.vehicle_number})")
            
            vehicle_str = " ".join(vehicle_parts) if vehicle_parts else "Vehicle details not specified"

            title = f"New Quick Service Request #{instance.id}"
            message = f"New Quick Service request from {instance.name} ({instance.phone_number}). {vehicle_str}"

            # 1. Create DB Notification records for each staff user
            notifications_to_create = [
                Notification(
                    user=staff_member,
                    title=title,
                    message=message,
                    notification_type='system'
                )
                for staff_member in staff_users
            ]
            Notification.objects.bulk_create(notifications_to_create)

            # 2. Optionally trigger FCM push notifications to staff users
            data = {
                'type': 'quick_service_request',
                'request_id': str(instance.id),
                'phone_number': instance.phone_number,
                'status': instance.status,
            }
            send_push_to_multiple(staff_users, title, message, data)

            logger.info("Created staff notifications for QuickServiceRequest #%s for %d staff users", instance.id, staff_users.count())

        except Exception as e:
            logger.error("Error creating staff notifications for QuickServiceRequest #%s: %s", instance.id, e)

    transaction.on_commit(send_staff_notifications)
