from django.contrib import admin
from django.utils.html import format_html
from .models import Payment, Refund


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "booking",
        "amount",
        "currency",
        "status",
        "payment_method",
        "refund_info",
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

    def refund_info(self, obj):
        total = obj.total_refunded
        if total > 0:
            return format_html(
                '<span style="color: orange;">₹{} refunded</span>', total
            )
        return '-'
    refund_info.short_description = 'Refunds'


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payment",
        "amount",
        "status_display",
        "reason",
        "requested_by",
        "processed_by",
        "requested_at",
    )
    list_filter = ("status", "reason", "requested_at")
    search_fields = (
        "payment__booking__id",
        "payment__razorpay_payment_id",
        "reason_detail",
    )
    readonly_fields = (
        "requested_at",
        "processed_at",
        "completed_at",
        "updated_at",
    )
    fieldsets = (
        (None, {
            'fields': ('payment', 'amount', 'currency', 'status')
        }),
        ('Reason', {
            'fields': ('reason', 'reason_detail')
        }),
        ('Processing', {
            'fields': ('requested_by', 'processed_by', 'staff_notes', 'razorpay_refund_id')
        }),
        ('Timestamps', {
            'classes': ('collapse',),
            'fields': ('requested_at', 'processed_at', 'completed_at', 'updated_at')
        }),
    )
    actions = ['approve_refunds', 'reject_refunds']

    def status_display(self, obj):
        colors = {
            'requested': '#f0ad4e',
            'approved': '#5bc0de',
            'rejected': '#d9534f',
            'processed': '#337ab7',
            'completed': '#5cb85c',
            'failed': '#d9534f',
        }
        color = colors.get(obj.status, '#777')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def approve_refunds(self, request, queryset):
        count = queryset.filter(status='requested').update(
            status='approved', processed_by=request.user
        )
        self.message_user(request, f"{count} refund(s) approved.")
    approve_refunds.short_description = "Approve selected refunds"

    def reject_refunds(self, request, queryset):
        count = queryset.filter(status='requested').update(
            status='rejected', processed_by=request.user
        )
        self.message_user(request, f"{count} refund(s) rejected.")
    reject_refunds.short_description = "Reject selected refunds"
