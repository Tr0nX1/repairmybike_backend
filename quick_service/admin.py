from django.contrib import admin
from .models import QuickServiceConfig, QuickServiceRequest

@admin.register(QuickServiceConfig)
class QuickServiceConfigAdmin(admin.ModelAdmin):
    list_display = ('title', 'base_price', 'support_phone', 'is_active', 'updated_at')
    list_editable = ('is_active',)

@admin.register(QuickServiceRequest)
class QuickServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'phone_number', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'phone_number', 'staff_notes')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Customer Info', {
            'fields': ('user', 'phone_number')
        }),
        ('Status & Progress', {
            'fields': ('status', 'staff_notes', 'services_grabbed', 'total_amount')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
