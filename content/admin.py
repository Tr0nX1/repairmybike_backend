from django.contrib import admin
from .models import CarouselItem, SupportOption

@admin.register(CarouselItem)
class CarouselItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active', 'created_at')
    list_editable = ('order', 'is_active')
    search_fields = ('title', 'subtitle')

@admin.register(SupportOption)
class SupportOptionAdmin(admin.ModelAdmin):
    list_display = ('title', 'option_type', 'value', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('option_type', 'is_active')
    search_fields = ('title', 'value')
