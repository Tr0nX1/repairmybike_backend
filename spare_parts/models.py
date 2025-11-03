from django.conf import settings
from django.db import models
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
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"


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