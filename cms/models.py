from django.db import models

class Banner(models.Model):
    title = models.CharField(max_length=255)
    image = models.ImageField(
        upload_to='cms/banners/',
        null=True, blank=True
    )
    image_url = models.URLField(
        blank=True,
        help_text='External URL fallback if no image uploaded'
    )
    link_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'banners'
        ordering = ['display_order', '-created_at']

    def __str__(self):
        return self.title
