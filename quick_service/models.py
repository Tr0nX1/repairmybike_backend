from django.db import models
from django.conf import settings

class QuickServiceConfig(models.Model):
    title = models.CharField(max_length=100, default="Quick Service")
    rules_html = models.TextField(help_text="Rules and pricing information in HTML or Markdown")
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    support_phone = models.CharField(max_length=20, help_text="The phone number user will call")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Quick Service Configuration"
        verbose_name_plural = "Quick Service Configurations"

    def __str__(self):
        return f"{self.title} (v{self.id})"

class QuickServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('contacted', 'Contacted'),
        ('mechanic_dispatched', 'Mechanic Dispatched'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quick_service_requests')
    phone_number = models.CharField(max_length=20, help_text="User's calling number")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    staff_notes = models.TextField(blank=True, null=True)
    services_grabbed = models.TextField(blank=True, null=True, help_text="Details of services provided")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"QS #{self.id} - {self.user.username} ({self.status})"
