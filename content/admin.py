from django.contrib import admin
from .models import StaticContent

@admin.register(StaticContent)
class StaticContentAdmin(admin.ModelAdmin):
    list_display = ('key', 'title', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('key', 'title', 'body')
