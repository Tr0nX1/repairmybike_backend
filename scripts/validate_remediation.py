import os
import django
import sys
from datetime import date, time
from decimal import Decimal

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from django.contrib.auth import get_user_model
from bookings.models import Booking, Customer
from vehicles.models import VehicleModel, VehicleBrand, VehicleType

User = get_user_model()

def validate():
    print("--- Validating Booking-Mechanic Relation ---")
    
    # Setup data
    username = 'test_mechanic_v2'
    User.objects.filter(username=username).delete()
    user = User.objects.create_user(username=username, password='password')
    
    vt, _ = VehicleType.objects.get_or_create(name='Scooter')
    vb, _ = VehicleBrand.objects.get_or_create(name='Honda', vehicle_type=vt)
    vm, _ = VehicleModel.objects.get_or_create(name='Activa', vehicle_brand=vb)
    customer, _ = Customer.objects.get_or_create(name='John Doe', phone='+919999999999')
    
    # 1. Booking accepts mechanic
    booking = Booking.objects.create(
        customer=customer,
        vehicle_model=vm,
        service_location='shop',
        appointment_date=date.today(),
        appointment_time=time(10, 0),
        total_amount=Decimal('500.00'),
        mechanic=user
    )
    if booking.mechanic == user:
        print("PASSED: Booking accepts mechanic.")
    else:
        print("FAILED: Booking does not accept mechanic.")
        return False
        
    if user.mechanic_bookings.count() == 1:
        print("PASSED: Reverse relation works.")
    else:
        print("FAILED: Reverse relation does not work.")
        return False
        
    # 2. Delete mechanic safely nullifies booking
    user_id = user.id
    user.delete()
    booking.refresh_from_db()
    if booking.mechanic is None:
        print("PASSED: Deleting mechanic nullifies booking (SET_NULL).")
    else:
        print("FAILED: Deleting mechanic does not nullify booking.")
        return False
        
    # Cleanup
    booking.delete()
    return True

if __name__ == "__main__":
    try:
        if validate():
            print("\nREMEDIATION VALIDATED SUCCESSFULLY")
        else:
            print("\nREMEDIATION VALIDATION FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\nERROR DURING VALIDATION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
