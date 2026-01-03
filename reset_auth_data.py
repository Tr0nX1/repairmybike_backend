from django.contrib.auth import get_user_model
from authentication.models import PhoneOTP, EmailOTP, OTPAttempt, UserSession

User = get_user_model()
print(f"Deleting {User.objects.count()} Users...")
User.objects.all().delete()

print(f"Deleting {PhoneOTP.objects.count()} PhoneOTPs...")
PhoneOTP.objects.all().delete()

print(f"Deleting {EmailOTP.objects.count()} EmailOTPs...")
EmailOTP.objects.all().delete()

print(f"Deleting {OTPAttempt.objects.count()} OTPAttempts...")
OTPAttempt.objects.all().delete()

print(f"Deleting {UserSession.objects.count()} UserSessions...")
UserSession.objects.all().delete()

print("Authentication data cleared successfully.")
