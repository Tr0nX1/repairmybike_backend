from django.db import models

class CarouselItem(models.Model):
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=200, blank=True, null=True)
    image = models.ImageField(upload_to='carousel/')
    action_link = models.CharField(max_length=200, blank=True, null=True, help_text="Internal route path or URL")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title

class SupportOption(models.Model):
    TYPE_CHOICES = (
        ('call', 'Call'),
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('website', 'Website'),
    )

    title = models.CharField(max_length=100)
    bg_color = models.CharField(max_length=50, blank=True, null=True, help_text="Hex color code")
    option_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    value = models.CharField(max_length=200, help_text="Phone number, email address, or URL")
    icon_image = models.ImageField(upload_to='support_icons/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']

    def __str__(self):
        return f"{self.title} ({self.get_option_type_display()})"
