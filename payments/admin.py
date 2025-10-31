from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "booking",
        "amount",
        "currency",
        "status",
        "payment_method",
        "created_at",
    )
    list_filter = ("status", "payment_method", "created_at")
    search_fields = (
        "booking__id",
        "razorpay_order_id",
        "razorpay_payment_id",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "razorpay_order_id",
        "razorpay_payment_id",
        "razorpay_signature",
        "error_code",
        "error_description",
    )
