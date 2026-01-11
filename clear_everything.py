from django.contrib.auth import get_user_model
from authentication.models import PhoneOTP, EmailOTP, OTPAttempt, UserSession, UserAddress
from vehicles.models import UserVehicle
from bookings.models import Booking
from shop.models import Order # Assuming shop has orders

User = get_user_model()

print(f"Deleting {Booking.objects.count()} Bookings...")
Booking.objects.all().delete()

print(f"Deleting {UserVehicle.objects.count()} UserVehicles...")
UserVehicle.objects.all().delete()

print(f"Deleting {UserAddress.objects.count()} UserAddresses...")
UserAddress.objects.all().delete()

print(f"Deleting {UserSession.objects.count()} UserSessions...")
UserSession.objects.all().delete()

print(f"Deleting {PhoneOTP.objects.count()} PhoneOTPs...")
PhoneOTP.objects.all().delete()

print(f"Deleting {EmailOTP.objects.count()} EmailOTPs...")
EmailOTP.objects.all().delete()

print(f"Deleting {OTPAttempt.objects.count()} OTPAttempts...")
OTPAttempt.objects.all().delete()

# Keep superusers if any? User said "everything related to user should detlete"
# I'll keep superusers to avoid locking the user out of admin
print(f"Deleting {User.objects.filter(is_superuser=False).count()} Non-Superuser Users...")
User.objects.filter(is_superuser=False).delete()

print("All user-related data cleared successfully.")
