from django.db import models
from django.conf import settings

class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('booking_update', 'Booking Update'),
        ('promotion', 'Promotion'),
        ('system', 'System'),
        ('payment', 'Payment'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"
