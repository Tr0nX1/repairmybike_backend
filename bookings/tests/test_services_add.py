from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from bookings.models import Booking, Customer, BookingService
from services.models import Service, ServiceCategory, ServicePricing
from vehicles.models import VehicleModel, VehicleBrand, VehicleType

User = get_user_model()


class AddServiceWorkflowTests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username='staff_service_test',
            password='password123',
            is_staff=True
        )
        self.customer = Customer.objects.create(name='Test Customer', phone='+919888888888')
        self.vtype = VehicleType.objects.create(name='Scooter')
        self.brand = VehicleBrand.objects.create(name='Honda', vehicle_type=self.vtype)
        self.vmodel = VehicleModel.objects.create(name='Activa 6G', vehicle_brand=self.brand)

        self.service_cat = ServiceCategory.objects.create(name='General Service')
        self.service = Service.objects.create(service_category=self.service_cat, name='Oil Change')
        self.pricing = ServicePricing.objects.create(
            service=self.service,
            vehicle_model=self.vmodel,
            price=Decimal('350.00')
        )

        self.booking = Booking.objects.create(
            customer=self.customer,
            vehicle_model=self.vmodel,
            service_location='shop',
            appointment_date=timezone.now().date(),
            appointment_time='10:00:00',
            total_amount=Decimal('0.00'),
            payment_method='cash',
            payment_status='pending',
            booking_status='in_progress'
        )

    def test_add_service_success(self):
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('staff-booking-add-service', kwargs={'pk': self.booking.id})
        response = self.client.post(url, {'service_id': self.service.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['error'], False)
        
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.total_amount, Decimal('350.00'))
        self.assertTrue(BookingService.objects.filter(booking=self.booking, service=self.service).exists())

    def test_cannot_add_duplicate_service(self):
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('staff-booking-add-service', kwargs={'pk': self.booking.id})
        self.client.post(url, {'service_id': self.service.id})
        response = self.client.post(url, {'service_id': self.service.id})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 'SERVICE_ALREADY_ADDED')

    def test_cannot_add_service_to_completed_booking(self):
        self.booking.booking_status = 'completed'
        self.booking.save()
        
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('staff-booking-add-service', kwargs={'pk': self.booking.id})
        response = self.client.post(url, {'service_id': self.service.id})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 'BOOKING_TERMINAL')

    def test_regular_staff_cannot_override_custom_price(self):
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('staff-booking-add-service', kwargs={'pk': self.booking.id})
        response = self.client.post(url, {'service_id': self.service.id, 'custom_price': '500.00'})
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['message'], 'Only managers or admins can override service price')

    def test_manager_can_override_custom_price(self):
        manager_user = User.objects.create_user(
            username='manager_service_test',
            password='password123',
            is_staff=True,
            is_manager=True
        )
        self.client.force_authenticate(user=manager_user)
        url = reverse('staff-booking-add-service', kwargs={'pk': self.booking.id})
        response = self.client.post(url, {'service_id': self.service.id, 'custom_price': '500.00'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.total_amount, Decimal('500.00'))

