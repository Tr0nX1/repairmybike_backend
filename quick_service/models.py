from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class QuickServiceConfig(models.Model):
    title = models.CharField(max_length=200, default="Instant Mechanic Support")
    rules_html = models.TextField(
        default="<p>1. Call us directly.<br>2. Mechanic dispatched within 30 mins.</p>"
    )
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=99.00)
    support_phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quick_service_config'
        verbose_name = 'Quick Service Configuration'
        verbose_name_plural = 'Quick Service Configurations'

    def __str__(self):
        return f"{self.title} (Active)" if self.is_active else f"{self.title} (Inactive)"

    @classmethod
    def get_solar_config(cls):
        """
        Singleton pattern manager method to return or create the active config row.
        """
        config = cls.objects.filter(is_active=True).first()
        if not config:
            config = cls.objects.create(
                title="Instant Mechanic Support",
                rules_html="<p>1. Call us directly.<br>2. Mechanic dispatched within 30 mins.</p>",
                base_price=99.00,
                support_phone="",
                is_active=True,
            )
        return config


class QuickServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('contacted', 'Contacted'),
        ('mechanic_dispatched', 'Mechanic Dispatched'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quick_service_requests',
        null=True,
        blank=True
    )
    guest_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=200, default="Valued Customer")
    phone_number = models.CharField(max_length=20)
    vehicle_number = models.CharField(max_length=20, blank=True, null=True)
    vehicle_manufacturer = models.CharField(max_length=100, blank=True, null=True)
    vehicle_model = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='initiated')
    staff_notes = models.TextField(blank=True, null=True)
    services_grabbed = models.TextField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quick_service_requests'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(guest_id__isnull=False),
                name='quick_service_request_user_or_guest_required'
            )
        ]

    def clean(self):
        super().clean()
        if not self.user and not self.guest_id:
            raise ValidationError("Either user or guest_id must be set for a QuickServiceRequest.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        owner = self.user.username if self.user else f"Guest ({self.guest_id})"
        return f"QuickService #{self.id} ({self.name} - {self.phone_number}) [{owner}] - {self.get_status_display()}"
