from django.contrib import admin

from .models import (
    SparePartCategory,
    SparePartBrand,
    SparePart,
    SparePartImage,
    SparePartFitment,
    Cart,
    CartItem,
    Order,
    OrderItem,
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


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("unit_price", "total_price")

    def total_price(self, obj):
        return obj.total_price


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer_name",
        "phone",
        "amount_total",
        "payment_status",
        "status",
        "created_at",
    )
    list_filter = ("payment_status", "status", "created_at")
    search_fields = ("customer_name", "phone", "session_id")
    readonly_fields = ("created_at", "updated_at")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "spare_part", "quantity", "unit_price")
    list_filter = ("spare_part",)