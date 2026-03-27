from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage'),
    ]

    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)
    
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount or percentage value")
    
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Minimum booking amount required")
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Maximum cap for percentage discounts")
    
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    
    usage_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Total number of times this coupon can be used")
    usage_count = models.PositiveIntegerField(default=0)
    
    user_limit = models.PositiveIntegerField(default=1, help_text="Number of times a single user can use this coupon")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'coupons'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()})"

    def is_valid(self, user=None, amount=0):
        now = timezone.now()
        
        if not self.is_active:
            return False, "Coupon is inactive"
            
        if now < self.start_date:
            return False, "Coupon is not yet active"
            
        if now > self.end_date:
            return False, "Coupon has expired"
            
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False, "Coupon usage limit reached"
            
        if amount < self.min_purchase_amount:
            return False, f"Minimum purchase amount of {self.min_purchase_amount} required"
            
        if user:
            user_usage = CouponUsage.objects.filter(coupon=self, user=user).count()
            if user_usage >= self.user_limit:
                return False, "You have already used this coupon"
                
        return True, ""

    def calculate_discount(self, amount):
        if self.discount_type == 'fixed':
            discount = self.value
        else:
            discount = (self.value / 100) * amount
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        
        return min(discount, amount)


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='coupon_usages')
    booking = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='coupon_redemptions')
    order = models.ForeignKey('spare_parts.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='coupon_redemptions')
    
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coupon_usage'
        ordering = ['-created_at']
