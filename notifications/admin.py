from django.contrib import admin
from .models import FCMDevice, NotificationLog

@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'token_snippet', 'platform', 'is_active', 'updated_at')
    list_filter = ('platform', 'is_active')
    search_fields = ('user__username', 'user__phone_number', 'token')
    
    def token_snippet(self, obj):
        return f"{obj.token[:20]}..."
    token_snippet.short_description = 'Token'

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'sent_at')
    list_filter = ('sent_at',)
    search_fields = ('user__username', 'title', 'body')
    readonly_fields = ('user', 'title', 'body', 'data', 'fcm_response', 'sent_at')
