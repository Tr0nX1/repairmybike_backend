import json
import logging
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
firebase_app = None

def get_firebase_app():
    """
    Get or initialize the Firebase Admin SDK singleton.
    Fails safely without raising exceptions if credentials are missing or invalid.
    """
    global firebase_app
    if firebase_app:
        return firebase_app
    try:
        firebase_app = firebase_admin.get_app()
        return firebase_app
    except ValueError:
        pass

    firebase_creds_json = getattr(settings, 'FIREBASE_CREDENTIALS_JSON', None)
    if firebase_creds_json and firebase_creds_json.strip():
        try:
            cred_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(cred_dict)
            firebase_app = firebase_admin.initialize_app(cred)
            logger.info("[OK] Firebase Admin SDK initialized")
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize Firebase Admin SDK: {e}")
            firebase_app = None
    else:
        logger.info("[INFO] FCM: No FIREBASE_CREDENTIALS_JSON provided. Push notifications are disabled.")
        firebase_app = None
    return firebase_app

# Initial attempt on module load
firebase_app = get_firebase_app()

def send_push_notification(user, title, body, data=None):
    """
    Send a single push notification to a user.
    """
    app = get_firebase_app()
    if not app:
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
        response = messaging.send(message, app=app)
        logger.info(f"FCM: Successfully sent message to user {user.id}: {response}")
        return True
    except Exception as e:
        logger.error(f"FCM: Failed to send message to user {user.id}: {e}")
        return False

def send_push_to_multiple(users, title, body, data=None):
    """
    Send push notifications to multiple users using multicast.
    """
    app = get_firebase_app()
    if not app:
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
        response = messaging.send_multicast(message, app=app)
        logger.info(f"FCM: Multicast success: {response.success_count}, failure: {response.failure_count}")
        return True
    except Exception as e:
        logger.error(f"FCM: Multicast failed: {e}")
        return False
