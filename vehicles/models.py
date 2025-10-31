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
