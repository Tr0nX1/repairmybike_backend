from django.test import TestCase
from django.urls import reverse


class BookingAPITests(TestCase):
    def test_list_requires_phone_query_param(self):
        url = reverse('booking-list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertTrue(data.get('error'))
        self.assertIn('phone', data.get('message', '').lower())
