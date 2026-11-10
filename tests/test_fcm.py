import json
from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings
from repairmybike import fcm

class FCMTests(TestCase):
    def setUp(self):
        # Reset cached app in fcm module for isolation
        fcm.firebase_app = None

    def tearDown(self):
        fcm.firebase_app = None

    @override_settings(FIREBASE_CREDENTIALS_JSON=None)
    def test_missing_credentials_returns_none_safely(self):
        """When FIREBASE_CREDENTIALS_JSON is None, get_firebase_app returns None without error."""
        with patch('firebase_admin.get_app', side_effect=ValueError("No app")):
            app = fcm.get_firebase_app()
            self.assertIsNone(app)

    @override_settings(FIREBASE_CREDENTIALS_JSON="")
    def test_empty_credentials_returns_none_safely(self):
        """When FIREBASE_CREDENTIALS_JSON is empty, get_firebase_app returns None."""
        with patch('firebase_admin.get_app', side_effect=ValueError("No app")):
            app = fcm.get_firebase_app()
            self.assertIsNone(app)

    @override_settings(FIREBASE_CREDENTIALS_JSON="{ invalid json")
    def test_malformed_json_handled_safely(self):
        """When FIREBASE_CREDENTIALS_JSON is malformed JSON, it logs error and returns None without raising."""
        with patch('firebase_admin.get_app', side_effect=ValueError("No app")):
            with self.assertLogs('repairmybike.fcm', level='ERROR') as cm:
                app = fcm.get_firebase_app()
                self.assertIsNone(app)
                self.assertTrue(any("Failed to initialize Firebase Admin SDK" in output for output in cm.output))

    @override_settings(FIREBASE_CREDENTIALS_JSON=None)
    def test_send_push_notification_no_app(self):
        """send_push_notification safely returns False when Firebase is not initialized."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.fcm_token = "some_token"
        with patch('firebase_admin.get_app', side_effect=ValueError("No app")):
            result = fcm.send_push_notification(mock_user, "Title", "Body")
            self.assertFalse(result)

    @override_settings(FIREBASE_CREDENTIALS_JSON=None)
    def test_send_push_notification_no_token(self):
        """send_push_notification safely returns False when user has no token."""
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.fcm_token = None
        result = fcm.send_push_notification(mock_user, "Title", "Body")
        self.assertFalse(result)

    @override_settings(FIREBASE_CREDENTIALS_JSON=None)
    def test_send_push_to_multiple_no_tokens(self):
        """send_push_to_multiple safely returns False when no user has a token."""
        mock_user1 = MagicMock()
        mock_user1.fcm_token = ""
        mock_user2 = MagicMock()
        mock_user2.fcm_token = None
        result = fcm.send_push_to_multiple([mock_user1, mock_user2], "Title", "Body")
        self.assertFalse(result)
