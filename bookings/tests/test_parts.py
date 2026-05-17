from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from bookings.models import Booking, Customer, BookingPart
from spare_parts.models import SparePart, SparePartCategory, SparePartBrand
from vehicles.models import VehicleModel, VehicleBrand, VehicleType

User = get_user_model()

class PartsWorkflowTests(APITestCase):
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
        
        # Setup data
        self.customer = Customer.objects.create(name='Test Customer', phone='+919999999999')
        self.vtype = VehicleType.objects.create(name='Test Type')
        self.brand = VehicleBrand.objects.create(name='Test Brand', vehicle_type=self.vtype)
        self.vmodel = VehicleModel.objects.create(name='Test Model', vehicle_brand=self.brand)
        
        self.sp_cat = SparePartCategory.objects.create(name='Parts', slug='parts')
        self.sp_brand = SparePartBrand.objects.create(name='Brand', slug='brand')
        
        self.part = SparePart.objects.create(
            category=self.sp_cat,
            brand=self.sp_brand,
            name='Test Part',
            slug='test-part',
            sku='SKU-001',
            mrp=100.00,
            sale_price=90.00,
            stock_qty=10
        )
        
        self.booking = Booking.objects.create(
            customer=self.customer,
            vehicle_model=self.vmodel,
            service_location='shop',
            appointment_date=timezone.now().date(),
            appointment_time='10:00:00',
            total_amount=Decimal('0.00'),
            payment_method='cash',
            payment_status='pending'
        )

    def test_cannot_add_part_with_insufficient_stock(self):
        """Returns 400 with meaningful message"""
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('staff-booking-add-part', kwargs={'pk': self.booking.id})
        
        # Request 100, but only 10 in stock
        data = {
            'part_id': self.part.id,
            'quantity': 100
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('stock', resp.data.get('message', '').lower())

    def test_price_locked_at_addition_time(self):
        """Changing part price after adding does not change BookingPart.unit_price"""
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('staff-booking-add-part', kwargs={'pk': self.booking.id})
        
        # Add part while price is 90
        self.client.post(url, {'part_id': self.part.id, 'quantity': 1}, format='json')
        
        # Verify BookingPart has 90
        bp = BookingPart.objects.get(booking=self.booking, spare_part=self.part)
        self.assertEqual(bp.unit_price, Decimal('90.00'))
        
        # Change part sale_price to 150
        self.part.sale_price = Decimal('150.00')
        self.part.save()
        
        # Verify BookingPart STILL has 90
        bp.refresh_from_db()
        self.assertEqual(bp.unit_price, Decimal('90.00'))

    def test_stock_deducted_only_once(self):
        """Saving completed booking twice only deducts stock once"""
        self.client.force_authenticate(user=self.staff_user)
        # Add and approve part
        url_add = reverse('staff-booking-add-part', kwargs={'pk': self.booking.id})
        self.client.post(url_add, {'part_id': self.part.id, 'quantity': 2}, format='json')
        
        bp = BookingPart.objects.get(booking=self.booking, spare_part=self.part)
        bp.approval_status = 'approved'
        bp.save()
        
        # Initial stock: 10
        # Complete booking
        self.booking.booking_status = 'completed'
        self.booking.save()
        
        self.part.refresh_from_db()
        self.assertEqual(self.part.stock_qty, 8) # 10 - 2
        
        # Save again as completed
        self.booking.save()
        self.part.refresh_from_db()
        self.assertEqual(self.part.stock_qty, 8) # Still 8

    def test_stock_reversed_on_cancellation(self):
        """Cancelling booking restores SparePart.stock_qty"""
        self.client.force_authenticate(user=self.staff_user)
        # Add and approve part
        url_add = reverse('staff-booking-add-part', kwargs={'pk': self.booking.id})
        self.client.post(url_add, {'part_id': self.part.id, 'quantity': 2}, format='json')
        bp = BookingPart.objects.get(booking=self.booking, spare_part=self.part)
        bp.approval_status = 'approved'
        bp.save()
        
        # Complete to deduct stock
        self.booking.booking_status = 'completed'
        self.booking.save()
        self.part.refresh_from_db()
        self.assertEqual(self.part.stock_qty, 8)
        
        # Cancel booking
        url_cancel = reverse('booking-cancel', kwargs={'pk': self.booking.id})
        resp = self.client.post(url_cancel, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        self.part.refresh_from_db()
        self.assertEqual(self.part.stock_qty, 10) # Restored

    def test_approved_part_requires_admin_to_remove(self):
        """Staff cannot remove approved part without admin permission"""
        self.client.force_authenticate(user=self.staff_user)
        # Add and approve part
        url_add = reverse('staff-booking-add-part', kwargs={'pk': self.booking.id})
        self.client.post(url_add, {'part_id': self.part.id, 'quantity': 1}, format='json')
        bp = BookingPart.objects.get(booking=self.booking, spare_part=self.part)
        bp.approval_status = 'approved'
        bp.save()
        
        # Attempt to remove as staff
        url_remove = reverse('staff-booking-remove-part', kwargs={'pk': self.booking.id})
        resp = self.client.post(url_remove, {'booking_part_id': bp.id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        
        # Attempt to remove as admin
        self.client.force_authenticate(user=self.admin_user)
        resp = self.client.post(url_remove, {'booking_part_id': bp.id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(BookingPart.objects.filter(id=bp.id).exists())
