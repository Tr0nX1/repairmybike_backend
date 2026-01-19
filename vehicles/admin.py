from django.contrib import admin
from repairmybike.admin_mixins import ImagePreviewMixin


from .models import VehicleType, VehicleBrand, VehicleModel


@admin.register(VehicleType)
class VehicleTypeAdmin(ImagePreviewMixin, admin.ModelAdmin):
    list_display = ("id", "name", "image_preview", "created_at", "updated_at")
    list_filter = ("created_at",)
    search_fields = ("name",)
    readonly_fields = ("image_preview", "created_at", "updated_at")



@admin.register(VehicleBrand)
class VehicleBrandAdmin(ImagePreviewMixin, admin.ModelAdmin):
    list_display = ("id", "name", "vehicle_type", "image_preview", "created_at")
    list_filter = ("vehicle_type", "created_at")
    search_fields = ("name", "vehicle_type__name")
    readonly_fields = ("image_preview", "created_at", "updated_at")



@admin.register(VehicleModel)
class VehicleModelAdmin(ImagePreviewMixin, admin.ModelAdmin):
    list_display = ("id", "name", "vehicle_brand", "image_preview", "created_at")
    list_filter = ("vehicle_brand", "created_at")
    search_fields = (
        "name",
        "vehicle_brand__name",
        "vehicle_brand__vehicle_type__name",
    )
    readonly_fields = ("image_preview", "created_at", "updated_at")

