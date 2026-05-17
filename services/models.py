from django.db import models
from vehicles.models import VehicleModel
from django.conf import settings
from authentication.models import GuestSession

class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=10, default='🔧')
    image = models.ImageField(upload_to='categories/images/', blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'service_categories'
        ordering = ['name']
        verbose_name_plural = 'Service Categories'
    
    def __str__(self):
        return self.name
        
    def get_service_count(self):
        return self.services.count()


class Service(models.Model):
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    reviews_count = models.PositiveIntegerField(default=0)
    specifications = models.JSONField(default=list)
    images = models.ImageField(upload_to='services/images/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'services'
        ordering = ['name']
        unique_together = ['service_category', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.service_category.name}"


class ServicePricing(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='pricing')
    vehicle_model = models.ForeignKey(VehicleModel, on_delete=models.CASCADE, related_name='service_pricing')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'service_pricing'
        ordering = ['service__name']
        unique_together = ['service', 'vehicle_model']
    
    def __str__(self):
        return f"{self.service.name} - {self.vehicle_model.name} - ₹{self.price}"


class UserSavedService(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_saved_services'
        unique_together = ['user', 'service']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.service}"


class GuestSavedService(models.Model):
    """Temporary storage for services saved by a guest"""
    guest_session = models.ForeignKey(GuestSession, on_delete=models.CASCADE, related_name='saved_services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'guest_saved_services'
        unique_together = ['guest_session', 'service']
        ordering = ['-created_at']

    def __str__(self):
        return f"Guest[{self.guest_session.guest_id}] - {self.service}"