from django.db import models

class VehicleType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    image = models.ImageField(upload_to='vehicle_types/', blank=True, null=True)  # ✅ added
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehicle_types'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class VehicleBrand(models.Model):
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.CASCADE, related_name='brands')
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='vehicle_brands/', blank=True, null=True)  # ✅ added
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehicle_brands'
        ordering = ['name']
        unique_together = ['vehicle_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.vehicle_type.name})"


class VehicleModel(models.Model):
    vehicle_brand = models.ForeignKey(VehicleBrand, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='vehicle_models/', blank=True, null=True)  # ✅ added
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehicle_models'
        ordering = ['name']
        unique_together = ['vehicle_brand', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.vehicle_brand.name}"


class UserVehicle(models.Model):
    user = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='vehicles')
    vehicle_model = models.ForeignKey(VehicleModel, on_delete=models.CASCADE, related_name='user_vehicles')
    registration_number = models.CharField(max_length=20, blank=True, null=True)
    last_service_date = models.DateField(blank=True, null=True)
    current_odometer = models.IntegerField(default=0, help_text="Last recorded odometer reading")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_vehicles'
        ordering = ['-is_default', '-created_at']
        unique_together = ['user', 'vehicle_model']

    def get_history(self):
        """Fetch all completed bookings for this user and vehicle model."""
        from bookings.models import Booking
        return Booking.objects.filter(
            customer__phone=self.user.phone_number,
            vehicle_model=self.vehicle_model,
            booking_status='completed'
        ).order_by('-appointment_date')
    
    def __str__(self):
        return f"{self.user} - {self.vehicle_model}"
