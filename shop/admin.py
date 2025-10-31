from django.contrib import admin
from .models import ShopInfo


@admin.register(ShopInfo)
class ShopInfoAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'name', 'phone', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'phone', 'address']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'address', 'phone', 'email', 'is_active')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Working Hours', {
            'fields': ('opening_time', 'closing_time', 'working_days')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )