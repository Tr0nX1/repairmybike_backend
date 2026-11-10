from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import Notification

User = get_user_model()

class NotificationSecurityTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(
            username='user_a',
            email='user_a@example.com',
            phone_number='+919999999991',
            password='Password123!'
        )
        self.user_b = User.objects.create_user(
            username='user_b',
            email='user_b@example.com',
            phone_number='+919999999992',
            password='Password123!'
        )
        self.notification_a = Notification.objects.create(
            user=self.user_a,
            title='User A Private Notification',
            message='Your service for bike A is scheduled',
            notification_type='system'
        )
        self.notification_b = Notification.objects.create(
            user=self.user_b,
            title='User B Private Notification',
            message='Your service for bike B is scheduled',
            notification_type='system'
        )

    def test_guest_with_header_gets_empty_list_and_200_ok(self):
        """Guest with X-Guest-ID receives 200 OK with empty list without 403 error."""
        self.client.credentials(HTTP_X_GUEST_ID='00000000-0000-4000-8000-000000000001')
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get('results', data)
        self.assertEqual(len(results), 0)

    def test_anonymous_without_header_gets_empty_list_and_200_ok(self):
        """Anonymous user receives 200 OK with empty list without 403 error."""
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get('results', data)
        self.assertEqual(len(results), 0)

    def test_user_a_cannot_see_user_b_notifications_in_list(self):
        """User A only sees their own notifications, never User B's."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get('results', data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.notification_a.id)
        self.assertEqual(results[0]['title'], 'User A Private Notification')

    def test_user_a_cannot_retrieve_user_b_notification_detail(self):
        """User A attempting to retrieve User B's notification detail receives 404."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(f'/api/notifications/{self.notification_b.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_guest_cannot_retrieve_any_notification_detail(self):
        """Guest attempting to retrieve any notification detail receives 404."""
        self.client.credentials(HTTP_X_GUEST_ID='00000000-0000-4000-8000-000000000001')
        response = self.client.get(f'/api/notifications/{self.notification_a.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_guest_cannot_mutate_notifications(self):
        """Guest cannot POST, PUT, PATCH, or DELETE notifications."""
        self.client.credentials(HTTP_X_GUEST_ID='00000000-0000-4000-8000-000000000001')
        
        # POST create
        post_res = self.client.post('/api/notifications/', {'title': 'Spam', 'message': 'test'})
        self.assertIn(post_res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

        # PUT update
        put_res = self.client.put(f'/api/notifications/{self.notification_a.id}/', {'title': 'Hacked'})
        self.assertIn(put_res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

        # PATCH update
        patch_res = self.client.patch(f'/api/notifications/{self.notification_a.id}/', {'is_read': True})
        self.assertIn(patch_res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

        # DELETE
        del_res = self.client.delete(f'/api/notifications/{self.notification_a.id}/')
        self.assertIn(del_res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

        # Custom actions
        action_res = self.client.post(f'/api/notifications/{self.notification_a.id}/mark-read/')
        self.assertIn(action_res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_guest_pagination_and_filtering_does_not_leak_notifications(self):
        """Filtering with query params (e.g. ?user_id=1, ?notification_type=system) never leaks private data to guests."""
        self.client.credentials(HTTP_X_GUEST_ID='00000000-0000-4000-8000-000000000001')
        
        response = self.client.get(f'/api/notifications/?user_id={self.user_a.id}&notification_type=system&page=1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get('results', data)
        self.assertEqual(len(results), 0)
