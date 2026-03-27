from django.db import models
from django.conf import settings
from bookings.models import Booking


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('created', 'Created'),
        ('authorized', 'Authorized'),
        ('captured', 'Captured'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='created')
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    error_code = models.CharField(max_length=100, blank=True, null=True)
    error_description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment for Booking #{self.booking.id} - {self.status}"

    @property
    def total_refunded(self):
        """Total amount refunded for this payment."""
        return self.refunds.filter(
            status__in=['processed', 'completed']
        ).aggregate(total=models.Sum('amount'))['total'] or 0

    @property
    def refundable_amount(self):
        """Amount still eligible for refund."""
        return self.amount - self.total_refunded


class Refund(models.Model):
    REFUND_STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    REFUND_REASON_CHOICES = [
        ('duplicate_payment', 'Duplicate Payment'),
        ('service_not_rendered', 'Service Not Rendered'),
        ('service_unsatisfactory', 'Service Unsatisfactory'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('overcharged', 'Overcharged'),
        ('other', 'Other'),
    ]

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default='requested')
    reason = models.CharField(max_length=30, choices=REFUND_REASON_CHOICES, default='other')
    reason_detail = models.TextField(blank=True, help_text="Additional details about the refund reason")
    
    # Razorpay refund tracking (for when payment gateway is enabled)
    razorpay_refund_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Staff tracking
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='refunds_requested'
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='refunds_processed'
    )
    
    # Audit fields
    staff_notes = models.TextField(blank=True, help_text="Internal notes for staff")
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'refunds'
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status'], name='refund_status_idx'),
            models.Index(fields=['payment'], name='refund_payment_idx'),
        ]
    
    def __str__(self):
        return f"Refund ₹{self.amount} for Payment #{self.payment.id} - {self.status}"