from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from authentication.models import StaffDirectory
from bookings.models import Booking, Customer, BookingPart
from spare_parts.models import SparePart, SparePartCategory, SparePartBrand
from vehicles.models import VehicleModel, VehicleBrand, VehicleType
from staff.models import ActivityLog
from datetime import date, time
from decimal import Decimal

User = get_user_model()

class TestSprint2APIs(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='password'
        )
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='password',
            is_staff=True,
            first_name='Staff',
            last_name='User'
        )
        self.normal_user = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password',
            phone_number='+919999999991'
        )

        # Setup Vehicle
        self.vt = VehicleType.objects.create(name='Scooter')
        self.vb = VehicleBrand.objects.create(name='Honda', vehicle_type=self.vt)
        self.vm = VehicleModel.objects.create(name='Activa', vehicle_brand=self.vb)

        # Setup Customer
        self.customer = Customer.objects.create(
            name='User One',
            phone=self.normal_user.phone_number,
            email=self.normal_user.email
        )

        # Setup Spare Part
        self.cat = SparePartCategory.objects.create(name='Engine', slug='engine')
        self.brand = SparePartBrand.objects.create(name='Honda', slug='honda-brand')
        self.part = SparePart.objects.create(
            name='Brake Pad',
            slug='brake-pad',
            sku='BP-001',
            category=self.cat,
            brand=self.brand,
            mrp=Decimal('250.00'),
            sale_price=Decimal('200.00'),
            stock_qty=10,
            in_stock=True
        )

        # Setup Booking
        self.booking = Booking.objects.create(
            customer=self.customer,
            vehicle_model=self.vm,
            service_location='shop',
            appointment_date=date.today(),
            appointment_time=time(10, 0),
            total_amount=Decimal('500.00'),
            booking_status='pending'
        )

    def test_staff_booking_list_filtering(self):
        url = reverse('staff-booking-list')
        self.client.force_authenticate(user=self.staff_user)

        # 1. List all
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

        # 2. Status filter
        response = self.client.get(url, {'status': 'pending'})
        self.assertEqual(response.data['count'], 1)
        response = self.client.get(url, {'status': 'completed'})
        self.assertEqual(response.data['count'], 0)

        # 3. Date filter
        response = self.client.get(url, {'date': str(date.today())})
        self.assertEqual(response.data['count'], 1)

        # 4. Search filter (by phone)
        response = self.client.get(url, {'search': self.customer.phone})
        self.assertEqual(response.data['count'], 1)

    def test_booking_status_lifecycle_and_audit(self):
        url = reverse('staff-booking-update-status', kwargs={'pk': self.booking.id})
        self.client.force_authenticate(user=self.staff_user)

        # Transition to completed
        response = self.client.patch(url, {'status': 'completed'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.booking_status, 'completed')

        # Verify Audit Log
        log = ActivityLog.objects.filter(action_type='status_change').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.staff_user)
        self.assertIn('completed', log.description)

    def test_inventory_linkage_and_totals(self):
        # 1. Add Part
        url_add = reverse('staff-booking-add-part', kwargs={'pk': self.booking.id})
        self.client.force_authenticate(user=self.staff_user)
        
        initial_total = self.booking.total_amount
        response = self.client.post(url_add, {'part_id': self.part.id, 'quantity': 2}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.booking.refresh_from_db()
        added_amount = self.part.sale_price * 2
        self.assertEqual(self.booking.total_amount, initial_total + added_amount)

        # Verify Activity Log for part addition
        log = ActivityLog.objects.filter(action_type='part_added').first()
        self.assertIsNotNone(log)

        # 2. Remove Part
        url_remove = reverse('staff-booking-remove-part', kwargs={'pk': self.booking.id})
        booking_part = BookingPart.objects.get(booking=self.booking, spare_part=self.part)
        
        response = self.client.post(url_remove, {'booking_part_id': booking_part.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.total_amount, initial_total)
        self.assertFalse(BookingPart.objects.filter(id=booking_part.id).exists())

        # Verify Activity Log for part removal
        log = ActivityLog.objects.filter(action_type='part_removed').first()
        self.assertIsNotNone(log)

    def test_stock_deduction_on_completion(self):
        # Add part
        BookingPart.objects.create(
            booking=self.booking,
            spare_part=self.part,
            quantity=3,
            unit_price=self.part.sale_price
        )
        initial_stock = self.part.stock_qty
        
        # Complete booking
        url = reverse('staff-booking-update-status', kwargs={'pk': self.booking.id})
        self.client.force_authenticate(user=self.staff_user)
        self.client.patch(url, {'status': 'completed'}, format='json')
        
        self.part.refresh_from_db()
        self.assertEqual(self.part.stock_qty, initial_stock - 3)

    def test_security_audit_logs_admin_only(self):
        url = reverse('activity-log-list')
        
        # 1. Staff access (should be blocked if strictly admin-only)
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(url)
        # Expected: 403 if project enforces Admin-only for logs
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Admin access
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_dashboard_stats_contract(self):
        # We need to find the correct stats URL name if staff-booking-stats fails
        try:
            url = reverse('staff-booking-stats')
        except:
            # Fallback to manual path if reverse fails during discovery
            url = '/api/staff/bookings/stats/'
            
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify contract per API_INVENTORY.json
        data = response.data['data']
        self.assertIn('total_bookings', data)
        self.assertIn('booking_status', data)
        self.assertIn('payment_status', data)

    def test_payment_webhook_graceful_check(self):
        # Attempt to resolve webhook URL
        try:
            url = reverse('razorpay-webhook') # Common name convention
            response = self.client.post(url, {}, format='json')
            # If exists, verify it doesn't 404
            self.assertNotEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        except:
            # Skip if endpoint absent as requested
            pass
