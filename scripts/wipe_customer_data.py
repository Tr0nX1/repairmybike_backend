from django.contrib.auth import get_user_model
from authentication.models import PhoneOTP, EmailOTP, OTPAttempt, UserSession
from bookings.models import Customer
from spare_parts.models import Order, Cart

User = get_user_model()

print("--- STARTING CUSTOMER DATA WIPE ---")

# 1. Bookings & Customers
# Note: Bookings cascade from Customer
c_count = Customer.objects.count()
Customer.objects.all().delete()
print(f"Deleted {c_count} Customers (and associated bookings).")

# 2. Orders & Carts
o_count = Order.objects.count()
Order.objects.all().delete()
print(f"Deleted {o_count} Orders.")

cart_count = Cart.objects.count()
Cart.objects.all().delete()
print(f"Deleted {cart_count} Carts.")

# 3. Auth
# Delete non-staff/non-superuser accounts
users = User.objects.filter(is_superuser=False, is_staff=False)
u_count = users.count()
users.delete()
print(f"Deleted {u_count} Customer User accounts.")

# Clear OTP logs
PhoneOTP.objects.all().delete()
EmailOTP.objects.all().delete()
OTPAttempt.objects.all().delete()
UserSession.objects.all().delete()
print("Declared OTP logs and sessions.")

print("--- WIPE COMPLETE ---")
