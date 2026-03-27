from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid


class User(AbstractUser):
    """Custom User model with Descope integration"""
    descope_user_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    profile_picture = models.URLField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    default_vehicle = models.ForeignKey('vehicles.VehicleModel', on_delete=models.SET_NULL, null=True, blank=True, related_name='users_default')
    
    # CRM Fields
    internal_notes = models.TextField(blank=True, help_text="Administrative notes about this user")
    total_ltv = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Lifetime value (total spend)")
    loyalty_points = models.PositiveIntegerField(default=0, help_text="Current balance of rewards points")
    
    # Referral Fields
    referral_code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            # Generate a unique referral code
            import string
            import random
            chars = string.ascii_uppercase + string.digits
            code = ''.join(random.choices(chars, k=8))
            # Ensure uniqueness
            while User.objects.filter(referral_code=code).exists():
                code = ''.join(random.choices(chars, k=8))
            self.referral_code = code
        super().save(*args, **kwargs)

    @property
    def is_high_value(self):
        return self.total_ltv > 5000 # Example threshold in INR
    
    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.phone_number or self.email or self.username


class UserAddress(models.Model):
    """Store detailed user address information"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    flat_house_no = models.CharField(max_length=255)
    area_street = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255, blank=True, null=True)
    pincode = models.CharField(max_length=10)
    town_city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    is_default = models.BooleanField(default=True)
    delivery_instructions = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name_plural = "User Addresses"

    def __str__(self):
        return f"{self.full_name} - {self.town_city} ({'Default' if self.is_default else ''})"


class UserSession(models.Model):
    """Track user sessions for Descope integration"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_token = models.CharField(max_length=2048, unique=True)
    refresh_token = models.CharField(max_length=2048, blank=True, null=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    # Optional metadata for better persistence and auditing
    device_id = models.CharField(max_length=255, blank=True, null=True)
    user_agent = models.CharField(max_length=500, blank=True, null=True)
    ip_address = models.CharField(max_length=100, blank=True, null=True)
    last_activity = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.session_token[:20]}..."


class PhoneOTP(models.Model):
    """Track phone OTP verification attempts"""
    phone_number = models.CharField(max_length=20)
    otp_code = models.CharField(max_length=10)
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'created_at']),
        ]
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def can_attempt(self):
        return self.attempts < self.max_attempts and not self.is_expired()
    
    def __str__(self):
        return f"{self.phone_number} - {self.otp_code} ({'verified' if self.is_verified else 'pending'})"


class EmailOTP(models.Model):
    """Track email OTP verification attempts"""
    email = models.EmailField()
    otp_code = models.CharField(max_length=10)
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'created_at']),
        ]
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def can_attempt(self):
        return self.attempts < self.max_attempts and not self.is_expired()
    
    def __str__(self):
        return f"{self.email} - {self.otp_code} ({'verified' if self.is_verified else 'pending'})"


class OTPAttempt(models.Model):
    """Track OTP attempts for rate limiting"""
    identifier = models.CharField(max_length=255)  # phone or email
    attempt_type = models.CharField(max_length=10, choices=[('phone', 'Phone'), ('email', 'Email')])
    attempts_count = models.PositiveIntegerField(default=0)
    last_attempt = models.DateTimeField(default=timezone.now)
    is_blocked = models.BooleanField(default=False)
    blocked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['identifier', 'attempt_type']
        indexes = [
            models.Index(fields=['identifier', 'attempt_type']),
        ]
    
    def is_blocked_now(self):
        if not self.is_blocked:
            return False
        if self.blocked_until and timezone.now() > self.blocked_until:
            self.is_blocked = False
            self.blocked_until = None
            self.save()
            return False
        return True
    
    def __str__(self):
        return f"{self.identifier} ({self.attempt_type}) - {self.attempts_count} attempts"


class StaffDirectory(models.Model):
    """Pre-provisioned staff directory to allow login without manual registration."""
    identifier = models.CharField(max_length=255, unique=True)  # email or phone
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_profile')
    name = models.CharField(max_length=255, blank=True, null=True)
    employee_id = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(max_length=100, blank=True, null=True)
    skills = models.JSONField(default=list, blank=True, help_text="List of service categories or specific skills")
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Staff Directory"
        indexes = [
            models.Index(fields=["identifier", "is_active"]),
            models.Index(fields=["is_available"]),
        ]

    def __str__(self):
        return f"{self.name or self.identifier} ({self.role})"


class GuestSession(models.Model):
    """Track guest sessions before they potentially sign up"""
    guest_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    device_id = models.CharField(max_length=255, blank=True, null=True)
    user_agent = models.CharField(max_length=500, blank=True, null=True)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    # Metadata for cart merging or context
    context_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Guest-{str(self.guest_id)[:8]}"

class ContactMessage(models.Model):
    """Store messages from the landing page contact form"""
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.name} - {self.email}"


class LoyaltyTransaction(models.Model):
    """Track points earned and redeemed by users"""
    TRANSACTION_TYPE_CHOICES = [
        ('earned', 'Earned'),
        ('redeemed', 'Redeemed'),
        ('expired', 'Expired'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loyalty_transactions')
    points = models.IntegerField()  # positive for earned, negative for redeemed
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    description = models.CharField(max_length=255)
    
    # Optional links to reference the source
    booking = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey('spare_parts.Order', on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.phone_number} - {self.points} pts ({self.transaction_type})"
