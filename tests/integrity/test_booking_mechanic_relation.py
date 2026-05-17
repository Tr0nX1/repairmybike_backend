import pytest
from django.contrib.auth import get_user_model
from bookings.models import Booking, Customer
from vehicles.models import VehicleModel, VehicleBrand, VehicleType
from datetime import date, time
from decimal import Decimal

User = get_user_model()

@pytest.mark.django_db
class TestBookingMechanicRelation:
    def setup_method(self):
        self.user = User.objects.create_user(username='mechanic1', password='password')
        self.vt = VehicleType.objects.create(name='Scooter')
        self.vb = VehicleBrand.objects.create(name='Honda', vehicle_type=self.vt)
        self.vm = VehicleModel.objects.create(name='Activa', vehicle_brand=self.vb)
        self.customer = Customer.objects.create(name='John Doe', phone='+919999999999')

    def test_booking_accepts_mechanic(self):
        booking = Booking.objects.create(
            customer=self.customer,
            vehicle_model=self.vm,
            service_location='shop',
            appointment_date=date.today(),
            appointment_time=time(10, 0),
            total_amount=Decimal('500.00'),
            mechanic=self.user
        )
        assert booking.mechanic == self.user
        assert self.user.mechanic_bookings.count() == 1

    def test_booking_accepts_null_mechanic(self):
        booking = Booking.objects.create(
            customer=self.customer,
            vehicle_model=self.vm,
            service_location='shop',
            appointment_date=date.today(),
            appointment_time=time(10, 0),
            total_amount=Decimal('500.00'),
            mechanic=None
        )
        assert booking.mechanic is None

    def test_delete_mechanic_safely_nullifies_booking(self):
        booking = Booking.objects.create(
            customer=self.customer,
            vehicle_model=self.vm,
            service_location='shop',
            appointment_date=date.today(),
            appointment_time=time(10, 0),
            total_amount=Decimal('500.00'),
            mechanic=self.user
        )
        self.user.delete()
        booking.refresh_from_db()
        assert booking.mechanic is None
