from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid


class User(AbstractUser):
    """Custom User model with Descope integration"""
    descope_user_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to='users/profiles/',
        null=True, blank=True
    )
    fcm_token = models.CharField(max_length=500, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    is_manager = models.BooleanField(default=False)
    default_vehicle = models.ForeignKey('vehicles.VehicleModel', on_delete=models.SET_NULL, null=True, blank=True, related_name='users_default')
    
    # Internal & Analytics Fields
    internal_notes = models.TextField(null=True, blank=True)
    total_ltv = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    loyalty_points = models.IntegerField(default=0)
    
    # Referral System
    referral_code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
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
    session_token = models.CharField(max_length=500, unique=True)
    refresh_token = models.CharField(max_length=500, blank=True, null=True)
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
    name = models.CharField(max_length=255, blank=True, null=True)
    employee_id = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(max_length=100, blank=True, null=True)
    photo = models.ImageField(
        upload_to='staff/photos/',
        null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["identifier", "is_active"]),
        ]

    def __str__(self):
        return f"{self.identifier} ({'active' if self.is_active else 'inactive'})"


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


class ContactSubmission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('replied', 'Replied'),
    ]

    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contact_submissions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.subject}"
