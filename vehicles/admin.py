from django.contrib import admin

from .models import VehicleType, VehicleBrand, VehicleModel


@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at", "updated_at")
    list_filter = ("created_at",)
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(VehicleBrand)
class VehicleBrandAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "vehicle_type", "created_at")
    list_filter = ("vehicle_type", "created_at")
    search_fields = ("name", "vehicle_type__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "vehicle_brand", "created_at")
    list_filter = ("vehicle_brand", "created_at")
    search_fields = (
        "name",
        "vehicle_brand__name",
        "vehicle_brand__vehicle_type__name",
    )
    readonly_fields = ("created_at", "updated_at")
