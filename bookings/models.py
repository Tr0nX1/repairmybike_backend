from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from vehicles.models import VehicleModel
from services.models import Service
from subscriptions.models import Subscription


phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)


class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(validators=[phone_regex], max_length=17, unique=True)
    email = models.EmailField(blank=True, null=True)
    internal_notes = models.TextField(default='')
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customers'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.phone}"


class Booking(models.Model):
    SERVICE_LOCATION_CHOICES = [
        ('home', 'Home Service'),
        ('shop', 'Visit Shop'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('razorpay', 'Razorpay'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]
    
    BOOKING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('en_route', 'En Route'),
        ('arrived', 'Arrived'),
        ('started', 'Started'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='bookings')
    mechanic = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mechanic_bookings'
    )
    vehicle_model = models.ForeignKey(VehicleModel, on_delete=models.CASCADE, related_name='bookings')
    service_location = models.CharField(max_length=10, choices=SERVICE_LOCATION_CHOICES)
    address = models.TextField(blank=True, null=True)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='cash')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='pending')
    booking_status = models.CharField(max_length=15, choices=BOOKING_STATUS_CHOICES, default='pending')
    
    # Optional link to a subscription; when completed, consumes a visit
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    # Internal flag to avoid double-counting visit consumption
    subscription_visit_consumed = models.BooleanField(default=False)
    # Internal flag to avoid double-deducting approved parts stock
    stock_deducted = models.BooleanField(default=False)
    
    # Fields found in DB but missing in simplified models.py
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    odometer_reading = models.IntegerField(blank=True, null=True)
    
    # Matching DB schema for notes
    customer_notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)
    staff_notes = models.TextField(blank=True, null=True)
    
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bookings'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'booking_status', 'appointment_date']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(total_amount__gte=0),
                name='booking_total_amount_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(discount_amount__gte=0),
                name='booking_discount_amount_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(booking_status__in=['pending', 'assigned', 'en_route', 'arrived', 'started', 'confirmed', 'in_progress', 'completed', 'cancelled']),
                name='booking_status_valid_choice'
            ),
        ]
    
    def __str__(self):
        return f"Booking #{self.id} - {self.customer.name}"


class BookingService(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booking_services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'booking_services'

    def __str__(self):
        return f"{self.booking.id} - {self.service.name}"


from spare_parts.models import SparePart


class BookingPart(models.Model):
    APPROVAL_PENDING = 'pending'
    APPROVAL_APPROVED = 'approved'
    APPROVAL_REJECTED = 'rejected'

    APPROVAL_STATUS_CHOICES = [
        (APPROVAL_PENDING, 'Pending'),
        (APPROVAL_APPROVED, 'Approved'),
        (APPROVAL_REJECTED, 'Rejected'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booking_parts')
    spare_part = models.ForeignKey(SparePart, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default=APPROVAL_PENDING)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_booking_parts'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    price_locked_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'booking_parts'
        constraints = [
            models.CheckConstraint(
                check=models.Q(unit_price__gte=0),
                name='bookingpart_unit_price_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(approval_status__in=['pending', 'approved', 'rejected']),
                name='bookingpart_approval_status_valid_choice'
            ),
        ]

    def __str__(self):
        return f"{self.id} - {self.spare_part.name} (x{self.quantity})"

    @property
    def total_price(self):
        return self.unit_price * self.quantity


class Feedback(models.Model):
    CATEGORY_CHOICES = [
        ('service', 'Service'),
        ('app', 'App'),
        ('complaint', 'Complaint'),
        ('suggestion', 'Suggestion'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks')
    rating = models.PositiveSmallIntegerField()  # Will add validation in serializer or clean
    comment = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'feedback'
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback {self.id} - {self.rating}/5"
