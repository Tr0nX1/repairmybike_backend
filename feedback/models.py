from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator

class Review(models.Model):
    REVIEW_TYPE_CHOICES = [
        ('SERVICE', 'Service'),
        ('PRODUCT', 'Product'),
        ('APP', 'App Experience'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    
    # Generic relation to target (Service or SparePart)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to={'model__in': ('service', 'sparepart')}, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Verification links
    booking = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    order = models.ForeignKey('spare_parts.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    
    review_type = models.CharField(max_length=20, choices=REVIEW_TYPE_CHOICES)
    
    # Blinkit-style multi-dimensional ratings
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], help_text="Overall rating")
    quality_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    behavior_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True, help_text="Staff behavior")
    app_rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], null=True, blank=True)
    
    comment = models.TextField(blank=True)
    chips = models.JSONField(default=list, blank=True, help_text="List of tags like 'On-Time', 'Professional'")
    
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reviews'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['review_type']),
        ]

    def __str__(self):
        return f"Review by {self.user} - {self.rating} stars"

class ReviewPhoto(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='reviews/photos/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'review_photos'


class IssueTicket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tickets')
    booking = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    order = models.ForeignKey('spare_parts.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', db_index=True)
    
    internal_notes = models.TextField(blank=True, help_text="Notes for staff/admins")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'issue_tickets'
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return f"Ticket #{self.id} - {self.subject} ({self.status})"
