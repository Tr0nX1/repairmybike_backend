from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.utils.text import slugify


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
    slug = models.SlugField(max_length=128, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='subscriptions/plans/', blank=True, null=True)

    # High-level tier to group related durations (Basic/Premium)
    tier = models.CharField(max_length=16, choices=TIER_CHOICES, default="basic", db_index=True)
    benefits = models.JSONField(default=dict, blank=True, help_text="Legacy JSON field")
    # List of included service names for membership display
    services = models.JSONField(default=list, blank=True, help_text="Legacy JSON field")
    
    # New structured fields
    included_services = models.ManyToManyField('services.Service', blank=True, related_name='subscription_plans')
    
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="The regular price")
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="The offer price (what user actually pays)")
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Legacy original price field")
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

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class PlanBenefit(models.Model):
    """Structured benefits for a subscription plan"""
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='benefits_list')
    text = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subscription_plan_benefits'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.plan.name} - {self.text[:30]}"


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
    # Auto-renewal tracking
    renewed_count = models.PositiveIntegerField(default=0, help_text="Number of times this subscription has been renewed")
    renewal_history = models.JSONField(default=list, blank=True, help_text="Audit trail of renewal events")
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

    def renew(self):
        """
        Renew the subscription for the next billing period.
        Returns True if renewed, False otherwise.
        """
        if self.status != 'active' or not self.auto_renew:
            return False

        old_end = self.end_date
        old_start = self.start_date

        # Set new period
        self.start_date = old_end or timezone.now()
        self.end_date = self.compute_end_date()
        self.next_billing_date = self.end_date
        self.visits_consumed = 0
        self.renewed_count += 1

        # Record in history
        history_entry = {
            'renewed_at': timezone.now().isoformat(),
            'renewal_number': self.renewed_count,
            'old_start': old_start.isoformat() if old_start else None,
            'old_end': old_end.isoformat() if old_end else None,
            'new_start': self.start_date.isoformat(),
            'new_end': self.end_date.isoformat() if self.end_date else None,
            'plan_name': self.plan.name,
            'plan_price': str(self.plan.discount_price or self.plan.price),
        }
        if not isinstance(self.renewal_history, list):
            self.renewal_history = []
        self.renewal_history.append(history_entry)

        self.save()
        return True

    @property
    def is_due_for_renewal(self):
        """Check if subscription is due for renewal."""
        if not self.auto_renew or self.status != 'active':
            return False
        if not self.next_billing_date:
            return False
        return self.next_billing_date <= timezone.now()

    @property
    def is_expired(self):
        """Check if subscription has passed its end date."""
        if not self.end_date:
            return False
        return self.end_date <= timezone.now()