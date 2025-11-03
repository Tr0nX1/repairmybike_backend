from django.contrib import admin

from .models import (
    SparePartCategory,
    SparePartBrand,
    SparePart,
    SparePartImage,
    SparePartFitment,
    Cart,
    CartItem,
)


@admin.register(SparePartCategory)
class SparePartCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "created_at")
    search_fields = ("name", "slug")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SparePartBrand)
class SparePartBrandAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "created_at")
    search_fields = ("name", "slug")
    readonly_fields = ("created_at", "updated_at")


class SparePartImageInline(admin.TabularInline):
    model = SparePartImage
    extra = 0


@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "sku",
        "brand",
        "category",
        "sale_price",
        "currency",
        "in_stock",
        "stock_qty",
    )
    list_filter = ("brand", "category", "in_stock")
    search_fields = ("name", "sku")
    readonly_fields = ("created_at", "updated_at")
    inlines = [SparePartImageInline]


@admin.register(SparePartFitment)
class SparePartFitmentAdmin(admin.ModelAdmin):
    list_display = ("id", "spare_part", "vehicle_model", "notes")
    list_filter = ("spare_part", "vehicle_model")
    search_fields = ("spare_part__sku", "vehicle_model__name")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "session_id", "user", "updated_at")
    search_fields = ("session_id", "user__username")
    inlines = [CartItemInline]