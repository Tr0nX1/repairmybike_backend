from django.contrib import admin
from repairmybike.admin_mixins import ImagePreviewMixin


from .models import ServiceCategory, Service, ServicePricing


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(ImagePreviewMixin, admin.ModelAdmin):
    list_display = ("id", "name", "image_preview", "created_at", "updated_at")
    list_filter = ("created_at",)
    search_fields = ("name",)
    readonly_fields = ("image_preview", "created_at", "updated_at")


@admin.register(Service)
class ServiceAdmin(ImagePreviewMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "service_category",
        "image_preview",
        "created_at",
    )
    list_filter = ("service_category", "created_at")
    search_fields = ("name", "service_category__name")
    readonly_fields = ("image_preview", "created_at", "updated_at")


    fieldsets = (
        (None, {
            'fields': ('service_category', 'name', 'description', 'specifications', 'images', 'is_featured')
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(ServicePricing)
class ServicePricingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "service",
        "vehicle_model",
        "price",
        "created_at",
    )
    list_filter = ("service", "vehicle_model", "created_at")
    search_fields = (
        "service__name",
        "vehicle_model__name",
        "vehicle_model__vehicle_brand__name",
    )
    readonly_fields = ("created_at", "updated_at")
