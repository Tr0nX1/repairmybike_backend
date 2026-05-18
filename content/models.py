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


class PolicyContent(models.Model):
    slug = models.SlugField(unique=True, max_length=100)
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'content_policy'
        verbose_name = 'Policy Content'
        verbose_name_plural = 'Policy Content'

    def __str__(self):
        return self.title
