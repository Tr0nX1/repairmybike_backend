import json
import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
firebase_app = None
if settings.FIREBASE_CREDENTIALS_JSON:
    try:
        cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
        cred = credentials.Certificate(cred_dict)
        firebase_app = firebase_admin.initialize_app(cred)
        logger.info("[OK] Firebase Admin SDK initialized")
    except Exception as e:
        logger.error(f"[ERROR] Failed to initialize Firebase Admin SDK: {e}")

def send_push_notification(user, title, body, data=None):
    """
    Send a single push notification to a user.
    """
    if not firebase_app:
        logger.warning("FCM: Firebase app not initialized. Skipping.")
        return False

    if not user or not user.fcm_token:
        logger.debug(f"FCM: User {user.id if user else 'Unknown'} has no FCM token. Skipping.")
        return False

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
        token=user.fcm_token,
    )

    try:
        response = messaging.send(message)
        logger.info(f"FCM: Successfully sent message to user {user.id}: {response}")
        return True
    except Exception as e:
        logger.error(f"FCM: Failed to send message to user {user.id}: {e}")
        return False

def send_push_to_multiple(users, title, body, data=None):
    """
    Send push notifications to multiple users using multicast.
    """
    if not firebase_app:
        logger.warning("FCM: Firebase app not initialized. Skipping.")
        return False

    tokens = [u.fcm_token for u in users if u.fcm_token]
    if not tokens:
        logger.debug("FCM: No users have FCM tokens. Skipping multicast.")
        return False

    # messaging.send_multicast handles up to 500 tokens
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
        tokens=tokens,
    )

    try:
        response = messaging.send_multicast(message)
        logger.info(f"FCM: Multicast success: {response.success_count}, failure: {response.failure_count}")
        return True
    except Exception as e:
        logger.error(f"FCM: Multicast failed: {e}")
        return False
