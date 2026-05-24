from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class CashSession(models.Model):
    STATUS_OPEN = 'open'
    STATUS_PENDING_APPROVAL = 'pending_approval'
    STATUS_APPROVED = 'approved'
    STATUS_FLAGGED = 'flagged'

    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_PENDING_APPROVAL, 'Pending Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_FLAGGED, 'Flagged'),
    ]

    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cash_sessions'
    )
    date = models.DateField()
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    expected_closing = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    variance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    notes = models.TextField(blank=True)
    approval_notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_cash_sessions'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'cash_sessions'
        ordering = ['-date', '-id']
        indexes = [
            models.Index(fields=['staff', 'date', 'status']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(opening_balance__gte=0),
                name='cashsession_opening_balance_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(closing_balance__gte=0) | models.Q(closing_balance__isnull=True),
                name='cashsession_closing_balance_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(status__in=['open', 'pending_approval', 'approved', 'flagged']),
                name='cashsession_status_valid_choice'
            ),
        ]

    def __str__(self):
        return f"{self.staff} - {self.date} ({self.status})"


class CashMovement(models.Model):
    TYPE_COLLECTION = 'collection'
    TYPE_EXPENSE = 'expense'
    TYPE_ADJUSTMENT = 'adjustment'
    VERIFICATION_PENDING = 'pending'
    VERIFICATION_VERIFIED = 'verified'

    MOVEMENT_TYPE_CHOICES = [
        (TYPE_COLLECTION, 'Collection'),
        (TYPE_EXPENSE, 'Expense'),
        (TYPE_ADJUSTMENT, 'Adjustment'),
    ]
    VERIFICATION_STATUS_CHOICES = [
        (VERIFICATION_PENDING, 'Pending'),
        (VERIFICATION_VERIFIED, 'Verified'),
    ]

    session = models.ForeignKey(CashSession, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cash_movements'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_cash_movements'
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default=VERIFICATION_PENDING
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_cash_movements'
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'cash_movements'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['session', 'movement_type']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='cashmovement_amount_positive'
            ),
        ]

    def __str__(self):
        return f"{self.movement_type} - {self.amount} ({self.session_id})"


class CashReconciliation(models.Model):
    session = models.ForeignKey(CashSession, on_delete=models.CASCADE, related_name='reconciliations')
    total_collections = models.DecimalField(max_digits=12, decimal_places=2)
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2)
    total_adjustments = models.DecimalField(max_digits=12, decimal_places=2)
    calculated_closing = models.DecimalField(max_digits=12, decimal_places=2)
    actual_closing = models.DecimalField(max_digits=12, decimal_places=2)
    variance = models.DecimalField(max_digits=12, decimal_places=2)
    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cash_reconciliations'
    )
    reconciled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cash_reconciliations'
        ordering = ['-reconciled_at']

    def __str__(self):
        return f"Reconciliation #{self.id} - {self.session_id}"


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('status_change', 'Status Change'),
        ('stock_update', 'Stock Update'),
        ('price_change', 'Price Change'),
        ('part_added', 'Part Added to Job'),
        ('part_removed', 'Part Removed from Job'),
        ('part_approved', 'Part Approved'),
        ('part_rejected', 'Part Rejected'),
        ('staff_created', 'Staff Created'),
        ('staff_deactivated', 'Staff Deactivated'),
        ('payment_verified', 'Payment Verified'),
        ('cash_collected', 'Cash Collected'),
        ('cash_reconciled', 'Cash Reconciled'),
        ('cash_session_opened', 'Cash Session Opened'),
        ('cash_session_closed', 'Cash Session Closed'),
        ('stock_deducted', 'Stock Deducted'),
        ('stock_reversed', 'Stock Reversed'),
        ('price_locked', 'Price Locked'),
        ('subscription_visits_adjusted', 'Subscription Visits Adjusted'),
        ('user_role_changed', 'User Role Changed'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('mechanic_assigned', 'Mechanic Assigned'),
        ('subscription_requested', 'Subscription Requested'),
        ('subscription_approved', 'Subscription Approved'),
        ('subscription_rejected', 'Subscription Rejected'),
        ('order_placed', 'Order Placed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='activity_logs')
    action_type = models.CharField(max_length=32, choices=ACTION_CHOICES)
    description = models.TextField()
    
    # Generic linkage to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    metadata = models.JSONField(default=dict, blank=True) # For storing old/new values
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'activity_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action_type', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.user} - {self.action_type} - {self.timestamp}"
