from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import Notification

User = get_user_model()

class NotificationPermissionTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            phone_number='+919999999991',
            password='Password123!'
        )
        self.notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            message='Your service is scheduled',
            notification_type='system'
        )

    def test_guest_can_safely_list_notifications_without_403(self):
        """Guests sending X-Guest-ID receive 200 OK with empty list instead of 403 Forbidden."""
        self.client.credentials(HTTP_X_GUEST_ID='00000000-0000-4000-8000-000000000001')
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should be empty pagination results or list
        data = response.json()
        results = data.get('results', data)
        self.assertEqual(len(results), 0)

    def test_authenticated_user_can_view_own_notifications(self):
        """Authenticated users can see their own notifications."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get('results', data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Test Notification')

    def test_guest_cannot_mutate_notifications(self):
        """Guests cannot mark notifications read or create notifications."""
        self.client.credentials(HTTP_X_GUEST_ID='00000000-0000-4000-8000-000000000001')
        response = self.client.post(f'/api/notifications/{self.notification.id}/mark-read/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
