from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from vehicles.models import VehicleModel, VehicleBrand, VehicleType


class SparePartCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='spare_parts/categories/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'spare_part_categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class SparePartBrand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    logo = models.ImageField(upload_to='spare_parts/brands/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'spare_part_brands'
        ordering = ['name']

    def __str__(self):
        return self.name


class SparePart(models.Model):
    category = models.ForeignKey(SparePartCategory, on_delete=models.PROTECT, related_name='parts')
    brand = models.ForeignKey(SparePartBrand, on_delete=models.PROTECT, related_name='parts')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    sku = models.CharField(max_length=100, unique=True)
    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True)
    specs = models.JSONField(default=dict, blank=True)  # arbitrary attributes like capacity_ah, technology, voltage
    warranty_months_total = models.IntegerField(default=0)
    warranty_free_months = models.IntegerField(default=0)
    warranty_pro_rata_months = models.IntegerField(default=0)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    in_stock = models.BooleanField(default=True)
    stock_qty = models.IntegerField(default=0)
    ean = models.CharField(max_length=50, blank=True, null=True)
    weight_grams = models.IntegerField(blank=True, null=True)
    length_mm = models.IntegerField(blank=True, null=True)
    width_mm = models.IntegerField(blank=True, null=True)
    height_mm = models.IntegerField(blank=True, null=True)
    rating_average = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.IntegerField(default=0)
    thumbnail = models.ImageField(
        upload_to='spare_parts/thumbnails/',
        null=True, blank=True,
        help_text='Primary display image for this part'
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'spare_parts'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['sku']),
            models.Index(fields=['brand', 'category']),
            models.Index(fields=['name', 'sale_price', 'stock_qty']),
            models.Index(fields=['category']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(mrp__gte=0),
                name='sparepart_mrp_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(sale_price__gte=0),
                name='sparepart_sale_price_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(stock_qty__gte=0),
                name='sparepart_stock_qty_non_negative'
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def save(self, *args, **kwargs):
        # Derive in_stock from stock_qty
        self.in_stock = self.stock_qty > 0
        
        # If update_fields is present, ensure in_stock is included if stock_qty is
        if 'update_fields' in kwargs and kwargs['update_fields'] is not None:
            update_fields = set(kwargs['update_fields'])
            if 'stock_qty' in update_fields:
                update_fields.add('in_stock')
            kwargs['update_fields'] = list(update_fields)
            
        super().save(*args, **kwargs)


class SparePartImage(models.Model):
    spare_part = models.ForeignKey(SparePart, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='spare_parts/images/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'spare_part_images'
        ordering = ['spare_part', 'sort_order']

    def __str__(self):
        return f"Image for {self.spare_part.name}"


class SparePartFitment(models.Model):
    spare_part = models.ForeignKey(SparePart, on_delete=models.CASCADE, related_name='fitments')
    vehicle_model = models.ForeignKey(VehicleModel, on_delete=models.CASCADE, related_name='spare_fitments')
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'spare_part_fitments'
        unique_together = ['spare_part', 'vehicle_model']

    def __str__(self):
        return f"{self.spare_part.sku} -> {self.vehicle_model.name}"


class Cart(models.Model):
    session_id = models.CharField(max_length=64, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'spare_part_carts'
        ordering = ['-updated_at']

    def __str__(self):
        return f"Cart {self.id} ({self.session_id})"

    @property
    def total_amount(self):
        return sum(item.total_price for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    spare_part = models.ForeignKey(SparePart, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'spare_part_cart_items'
        unique_together = ['cart', 'spare_part']

    def __str__(self):
        return f"{self.spare_part.sku} x {self.quantity}"

    @property
    def total_price(self):
        return self.unit_price * self.quantity


class Order(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('cash_due', 'Cash Due'),
        ('cash_paid', 'Cash Paid'),
    ]
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('confirmed', 'Confirmed'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
    ]

    session_id = models.CharField(max_length=64, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    customer_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, db_index=True)
    address = models.TextField()
    amount_total = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    payment_method = models.CharField(max_length=20, default='cash')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='cash_due')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tracking_number = models.CharField(max_length=100, null=True, blank=True)
    courier_name = models.CharField(max_length=100, null=True, blank=True)
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)


    class Meta:
        db_table = 'spare_part_orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', 'created_at']),
            models.Index(fields=['session_id']),
        ]

    def __str__(self):
        return f"Order {self.id} ({self.session_id})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    spare_part = models.ForeignKey(SparePart, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'spare_part_order_items'

    @property
    def total_price(self):
        return self.unit_price * self.quantity

class UserSavedPart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_parts')
    spare_part = models.ForeignKey(SparePart, on_delete=models.CASCADE, related_name='saved_by_users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_saved_parts'
        unique_together = ['user', 'spare_part']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.spare_part}"


class GuestSavedPart(models.Model):
    guest_session = models.ForeignKey('authentication.GuestSession', on_delete=models.CASCADE, related_name='saved_parts')
    spare_part = models.ForeignKey(SparePart, on_delete=models.CASCADE, related_name='saved_by_guests')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'guest_saved_parts'
        unique_together = ['guest_session', 'spare_part']
        ordering = ['-created_at']

    def __str__(self):
        return f"Guest {self.guest_session.guest_id} - {self.spare_part}"
