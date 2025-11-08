from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator


class Plan(models.Model):
    TIER_CHOICES = [
        ("basic", "Basic"),
        ("premium", "Premium"),
    ]
    BILLING_PERIOD_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("half_yearly", "Half Yearly"),
        ("yearly", "Yearly"),
        # Keep 'annual' for backward compatibility with existing data
        ("annual", "Annual"),
    ]

    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(max_length=128, unique=True)
    description = models.TextField(blank=True)
    # High-level tier to group related durations (Basic/Premium)
    tier = models.CharField(max_length=16, choices=TIER_CHOICES, default="basic", db_index=True)
    benefits = models.JSONField(default=dict, blank=True)
    # List of included service names for membership display
    services = models.JSONField(default=list, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=8, default="INR")
    billing_period = models.CharField(max_length=16, choices=BILLING_PERIOD_CHOICES, default="monthly")
    # Number of included service visits within the billing period (e.g., Quarterly = 3)
    included_visits = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    razorpay_plan_id = models.CharField(max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["slug"], name="subscriptions_plan_slug_idx"),
            models.Index(fields=["active"], name="subscriptions_plan_active_idx"),
            models.Index(fields=["tier"], name="subscriptions_plan_tier_idx"),
        ]

    def __str__(self):
        return self.name


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("canceled", "Canceled"),
        ("expired", "Expired"),
    ]

    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    user = models.ForeignKey(getattr(settings, "AUTH_USER_MODEL", "auth.User"), on_delete=models.SET_NULL, null=True, blank=True, related_name="subscriptions")
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(
        max_length=17,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be in the format '+999999999' (up to 15 digits).",
            )
        ],
        db_index=True,
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    auto_renew = models.BooleanField(default=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)
    next_billing_date = models.DateTimeField(blank=True, null=True)
    razorpay_subscription_id = models.CharField(max_length=128, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    # Track how many visits have been consumed in the current period
    visits_consumed = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"], name="subscriptions_status_idx"),
            models.Index(fields=["user"], name="subscriptions_user_idx"),
            models.Index(fields=["contact_phone"], name="subscriptions_phone_idx"),
        ]

    def __str__(self):
        return f"{self.plan.name} - {self.status}"

    def compute_end_date(self):
        period = self.plan.billing_period
        if period == "monthly":
            return self.start_date + timezone.timedelta(days=30)
        if period == "quarterly":
            return self.start_date + timezone.timedelta(days=90)
        if period == "half_yearly":
            return self.start_date + timezone.timedelta(days=182)
        if period in ("yearly", "annual"):
            return self.start_date + timezone.timedelta(days=365)
        return None

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.compute_end_date()
        if not self.next_billing_date and self.end_date:
            self.next_billing_date = self.end_date
        super().save(*args, **kwargs)