from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from authentication.models import StaffDirectory
from bookings.models import Booking, Customer
from vehicles.models import VehicleModel, VehicleBrand, VehicleType
from datetime import date, time
from decimal import Decimal

User = get_user_model()

class TestSprint1APIs(TestCase):
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

        StaffDirectory.objects.create(
            identifier='staff_dir@example.com',
            name='Dir Staff',
            employee_id='EMP-001',
            role='mechanic',
            is_active=True
        )

    def test_staff_directory_contract_and_admin_only(self):
        url = reverse('staff-list')

        # Normal user cannot access
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Admin can access
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data.get('results', response.data)
        item = data[0]
        expected_keys = {
            'id', 'name', 'employee_id', 'role', 'is_active', 'email', 'created_at'
        }
        self.assertTrue(expected_keys.issubset(set(item.keys())))
        self.assertNotIn('identifier', item)

        # email is derived from identifier containing '@'
        self.assertEqual(item['email'], 'staff_dir@example.com')

    def test_staff_directory_filter_search_and_ordering(self):
        url = reverse('staff-list')

        self.client.force_authenticate(user=self.admin_user)

        # Filtering: role
        response = self.client.get(url, {'role': 'mechanic'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Searching: name / employee_id
        response = self.client.get(url, {'search': 'EMP-001'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(url, {'search': 'Dir Staff'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ordering (sanity check)
        response = self.client.get(url, {'ordering': 'name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_crm_list_admin_only(self):
        url = reverse('customers-list')

        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_crm_aggregation_and_contract(self):
        vt = VehicleType.objects.create(name='Scooter')
        vb = VehicleBrand.objects.create(name='Honda', vehicle_type=vt)
        vm = VehicleModel.objects.create(name='Activa', vehicle_brand=vb)

        customer = Customer.objects.create(
            name='User One',
            phone=self.normal_user.phone_number,
            email=self.normal_user.email
        )

        Booking.objects.create(
            customer=customer,
            vehicle_model=vm,
            service_location='shop',
            appointment_date=date.today(),
            appointment_time=time(10, 0),
            total_amount=Decimal('500.00'),
            booking_status='completed'
        )

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('customers-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data.get('results', response.data)
        user_data = next(
            (u for u in data if u['email'] == self.normal_user.email),
            None
        )
        self.assertIsNotNone(user_data)
        self.assertEqual(user_data['total_bookings'], 1)
        self.assertEqual(user_data['phone_number'], self.normal_user.phone_number)

        expected_keys = {
            'id', 'full_name', 'phone_number', 'email', 'total_ltv',
            'loyalty_points', 'referral_code', 'referred_by', 'total_bookings',
            'active_subscriptions', 'last_visit', 'created_at'
        }
        self.assertTrue(expected_keys.issubset(set(user_data.keys())))

    def test_booking_serializer_mechanic_contract_has_mechanic_id(self):
        vt = VehicleType.objects.create(name='Scooter')
        vb = VehicleBrand.objects.create(name='Honda', vehicle_type=vt)
        vm = VehicleModel.objects.create(name='Activa', vehicle_brand=vb)
        customer = Customer.objects.create(
            name='User One',
            phone=self.normal_user.phone_number,
            email=self.normal_user.email
        )

        booking = Booking.objects.create(
            customer=customer,
            vehicle_model=vm,
            service_location='shop',
            appointment_date=date.today(),
            appointment_time=time(10, 0),
            total_amount=Decimal('500.00'),
            mechanic=self.staff_user
        )

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('staff-booking-detail', kwargs={'pk': booking.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payload = response.data['data']
        self.assertEqual(payload['mechanic'], self.staff_user.id)
        self.assertEqual(payload['mechanic_name'], self.staff_user.get_full_name())
        self.assertIn('mechanic_id', payload)
        self.assertEqual(payload['mechanic_id'], self.staff_user.id)
