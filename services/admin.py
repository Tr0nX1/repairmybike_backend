from django.contrib import admin

from .models import ServiceCategory, Service, ServicePricing


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at", "updated_at")
    list_filter = ("created_at",)
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "service_category",
        "created_at",
    )
    list_filter = ("service_category", "created_at")
    search_fields = ("name", "service_category__name")
    readonly_fields = ("created_at", "updated_at")


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
