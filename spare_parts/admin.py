from django.contrib import admin
from repairmybike.admin_mixins import ImagePreviewMixin, StatusColorMixin


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
    ShipmentUpdate,
)


@admin.register(SparePartCategory)
class SparePartCategoryAdmin(ImagePreviewMixin, admin.ModelAdmin):
    list_display = ("id", "name", "slug", "image_preview", "created_at")
    search_fields = ("name", "slug")
    readonly_fields = ("image_preview", "created_at", "updated_at")



@admin.register(SparePartBrand)
class SparePartBrandAdmin(ImagePreviewMixin, admin.ModelAdmin):
    list_display = ("id", "name", "slug", "image_preview", "created_at")
    search_fields = ("name", "slug")
    readonly_fields = ("image_preview", "created_at", "updated_at")



class SparePartImageInline(ImagePreviewMixin, admin.TabularInline):
    model = SparePartImage
    extra = 0
    readonly_fields = ("image_preview",)



@admin.register(SparePart)
class SparePartAdmin(ImagePreviewMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "sku",
        "brand",
        "category",
        "mrp",
        "sale_price",
        "image_preview",
        "in_stock",
    )
    list_filter = ("brand", "category", "in_stock")
    search_fields = ("name", "sku")
    list_editable = ("sale_price", "in_stock")
    readonly_fields = ("image_preview", "created_at", "updated_at")
    inlines = [SparePartImageInline]

    def image_preview(self, obj):
        # Show primary image if available
        primary = obj.images.filter(is_primary=True).first() or obj.images.first()
        if primary:
            return super().image_preview(primary)
        return "No Image"
    image_preview.short_description = 'Preview'



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


class ShipmentUpdateInline(admin.TabularInline):
    model = ShipmentUpdate
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Order)
class OrderAdmin(StatusColorMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "customer_name",
        "phone",
        "amount_total",
        "payment_status_display",
        "order_status_display",
        "created_at",
    )
    list_filter = ("payment_status", "status", "created_at")
    search_fields = ("customer_name", "phone", "session_id")
    readonly_fields = ("created_at", "updated_at")
    inlines = [OrderItemInline, ShipmentUpdateInline]
    actions = ['mark_as_paid', 'mark_as_shipped']

    def payment_status_display(self, obj):
        return self.colored_status(obj, 'payment_status')
    payment_status_display.short_description = 'Payment'

    def order_status_display(self, obj):
        return self.colored_status(obj, 'status')
    order_status_display.short_description = 'Status'

    def mark_as_paid(self, request, queryset):
        rows_updated = queryset.update(payment_status='paid')
        self.message_user(request, f"{rows_updated} orders marked as paid.")
    mark_as_paid.short_description = "Mark selected orders as Paid"

    def mark_as_shipped(self, request, queryset):
        rows_updated = queryset.update(status='shipped')
        self.message_user(request, f"{rows_updated} orders marked as Shipped.")
    mark_as_shipped.short_description = "Mark selected orders as Shipped"

    fieldsets = (
        (None, {
            'fields': ('session_id', 'user', 'customer_name', 'phone', 'address', 'amount_total')
        }),
        ('Status', {
            'fields': ('status', 'payment_status', 'payment_method')
        }),
        ('Shipping & Tracking', {
            'fields': (
                'shipping_method', 'address_details', 
                'tracking_number', 'courier_name', 'courier_tracking_url',
                'estimated_delivery', 'shipped_at', 'delivered_at'
            )
        }),
        ('Important Dates', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ShipmentUpdate)
class ShipmentUpdateAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'status', 'location', 'timestamp', 'created_by')
    list_filter = ('status', 'timestamp')
    search_fields = ('order__id', 'location', 'note')
    readonly_fields = ('created_at',)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "spare_part", "quantity", "unit_price")
    list_filter = ("spare_part",)
