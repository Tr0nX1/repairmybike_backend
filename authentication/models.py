from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Custom User model with Descope integration"""
    descope_user_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    profile_picture = models.URLField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.phone_number or self.email or self.username


class UserSession(models.Model):
    """Track user sessions for Descope integration"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_token = models.CharField(max_length=500, unique=True)
    refresh_token = models.CharField(max_length=500, blank=True, null=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
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