from django.db import models

class StaticContent(models.Model):
    key = models.SlugField(unique=True, max_length=100)
    title = models.CharField(max_length=255)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'static_content'
        verbose_name = 'Static Content'
        verbose_name_plural = 'Static Content'

    def __str__(self):
        return self.title
