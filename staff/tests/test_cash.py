from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from staff.models import CashSession, CashMovement, CashReconciliation
from bookings.models import Booking, Customer
from vehicles.models import VehicleModel, VehicleBrand, VehicleType

User = get_user_model()

class CashSessionTests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username='staff_test',
            password='password123',
            is_staff=True
        )
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='password123',
            is_superuser=True
        )
        
        # Setup data for booking collection
        self.customer = Customer.objects.create(name='Test Customer', phone='+919999999999')
        self.vtype = VehicleType.objects.create(name='Test Type')
        self.brand = VehicleBrand.objects.create(name='Test Brand', vehicle_type=self.vtype)
        self.vmodel = VehicleModel.objects.create(name='Test Model', vehicle_brand=self.brand)
        
        self.booking = Booking.objects.create(
            customer=self.customer,
            vehicle_model=self.vmodel,
            service_location='shop',
            appointment_date=timezone.now().date(),
            appointment_time='10:00:00',
            total_amount=Decimal('500.00'),
            payment_method='cash',
            payment_status='pending'
        )

    def test_cannot_open_duplicate_session(self):
        """Same staff opening session twice same day returns 400"""
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('cash-session-start')
        
        # First opening
        resp = self.client.post(url, {'opening_balance': 1000}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        
        # Second opening
        resp = self.client.post(url, {'opening_balance': 1000}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(resp.data.get('error'))

    def test_cash_collection_updates_booking_payment_status(self):
        """After collect, booking.payment_status == 'completed'"""
        self.client.force_authenticate(user=self.staff_user)
        # Open session
        self.client.post(reverse('cash-session-start'), {'opening_balance': 0}, format='json')
        
        url = reverse('staff-payment-collect')
        data = {
            'booking_id': self.booking.id,
            'amount': 500.00
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, 'completed')

    def test_variance_over_100_sets_pending_approval(self):
        """Close session with variance >100 sets status='pending_approval'"""
        self.client.force_authenticate(user=self.staff_user)
        # Open with 0
        self.client.post(reverse('cash-session-start'), {'opening_balance': 0}, format='json')
        
        # Collect 500
        self.client.post(reverse('staff-payment-collect'), {'booking_id': self.booking.id, 'amount': 500}, format='json')
        
        # Expected: 500. Actual: 700. Variance: 200 (> 100)
        session = CashSession.objects.filter(staff=self.staff_user, status='open').first()
        url = reverse('cash-session-close', kwargs={'pk': session.id})
        resp = self.client.post(url, {'actual_closing_balance': 700}, format='json')
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertEqual(session.status, 'pending_approval')
        self.assertEqual(session.variance, Decimal('200.00'))

    def test_variance_under_100_auto_approves(self):
        """Close with variance <=100 sets status='approved'"""
        self.client.force_authenticate(user=self.staff_user)
        self.client.post(reverse('cash-session-start'), {'opening_balance': 0}, format='json')
        self.client.post(reverse('staff-payment-collect'), {'booking_id': self.booking.id, 'amount': 500}, format='json')
        
        # Expected: 500. Actual: 550. Variance: 50 (<= 100)
        session = CashSession.objects.filter(staff=self.staff_user, status='open').first()
        url = reverse('cash-session-close', kwargs={'pk': session.id})
        resp = self.client.post(url, {'actual_closing_balance': 550}, format='json')
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertEqual(session.status, 'approved')

    def test_cannot_add_movement_to_closed_session(self):
        """Adding movement after session closed returns 400"""
        self.client.force_authenticate(user=self.staff_user)
        # Open
        self.client.post(reverse('cash-session-start'), {'opening_balance': 0}, format='json')
        session = CashSession.objects.filter(staff=self.staff_user, status='open').first()
        
        # Close
        self.client.post(reverse('cash-session-close', kwargs={'pk': session.id}), {'actual_closing_balance': 0}, format='json')
        
        # Try to collect
        url = reverse('staff-payment-collect')
        # We need another booking to avoid "already collected" error if that's checked first
        booking2 = Booking.objects.create(
            customer=self.customer,
            vehicle_model=self.vmodel,
            service_location='shop',
            appointment_date=timezone.now().date(),
            appointment_time='11:00:00',
            total_amount=Decimal('100.00'),
            payment_method='cash'
        )
        
        resp = self.client.post(url, {'booking_id': booking2.id, 'amount': 100}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('No open cash session', resp.data.get('message', ''))
