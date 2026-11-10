from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from unittest.mock import patch
from django.db import OperationalError

class HealthCheckTestCase(TestCase):
    def test_readiness_check_returns_200(self):
        response = self.client.get('/ready/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'ready')

    def test_health_check_healthy_when_db_ok(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'healthy')
        self.assertEqual(data.get('database'), 'connected')

    @patch('django.db.connection.cursor')
    def test_health_check_handles_db_down_gracefully_without_unhandled_500(self, mock_cursor):
        mock_cursor.side_effect = OperationalError("connection to server failed")
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data.get('status'), 'degraded')
        self.assertEqual(data.get('database'), 'disconnected')
