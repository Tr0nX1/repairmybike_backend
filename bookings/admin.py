from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from repairmybike.admin_mixins import StatusColorMixin

from .models import Customer, Booking, BookingService, Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'booking', 'rating', 'category', 'status', 'created_at')
    list_filter = ('status', 'category', 'rating', 'created_at')
    search_fields = ('comment', 'user__username', 'booking__id')
    readonly_fields = ('created_at',)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "email", "orders_link", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "phone", "email")
    readonly_fields = ("created_at", "updated_at")

    def orders_link(self, obj):
        url = reverse('admin:spare_parts_order_changelist') + f'?q={obj.phone}'
        return format_html('<a href="{}">View Orders</a>', url)
    orders_link.short_description = 'History'


class BookingServiceInline(admin.TabularInline):
    model = BookingService
    extra = 0
    readonly_fields = ("price",)


@admin.register(Booking)
class BookingAdmin(StatusColorMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "vehicle_model",
        "service_location_display",
        "appointment_display",
        "total_amount",
        "payment_status_display",
        "booking_status_display",
        "created_at",
    )
    list_filter = (
        "service_location",
        "payment_status",
        "booking_status",
        "appointment_date",
        "created_at",
    )
    search_fields = (
        "customer__name",
        "customer__phone",
        "vehicle_model__name",
        "vehicle_model__vehicle_brand__name",
    )
    readonly_fields = ("created_at", "updated_at")
    inlines = [BookingServiceInline]
    actions = ['mark_as_confirmed', 'mark_as_paid', 'mark_as_completed']

    def service_location_display(self, obj):
        icon = "🏠" if obj.service_location == 'home' else "🏬"
        return format_html('<span>{} {}</span>', icon, obj.get_service_location_display())
    service_location_display.short_description = 'Location'

    def appointment_display(self, obj):
        return format_html('<b>{}</b><br><small>{}</small>', obj.appointment_date, obj.appointment_time)
    appointment_display.short_description = 'Appointment'

    def payment_status_display(self, obj):
        return self.colored_status(obj, 'payment_status')
    payment_status_display.short_description = 'Payment'

    def booking_status_display(self, obj):
        return self.colored_status(obj, 'booking_status')
    booking_status_display.short_description = 'Status'

    def mark_as_confirmed(self, request, queryset):
        rows_updated = queryset.update(booking_status='confirmed')
        self.message_user(request, f"{rows_updated} bookings marked as confirmed.")
    mark_as_confirmed.short_description = "Confirm selected bookings"

    def mark_as_paid(self, request, queryset):
        rows_updated = queryset.update(payment_status='paid')
        self.message_user(request, f"{rows_updated} bookings marked as paid.")
    mark_as_paid.short_description = "Mark selected bookings as Paid"

    def mark_as_completed(self, request, queryset):
        rows_updated = queryset.update(booking_status='completed')
        self.message_user(request, f"{rows_updated} bookings marked as completed.")
    mark_as_completed.short_description = "Mark selected bookings as Completed"


@admin.register(BookingService)
class BookingServiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "booking",
        "service",
        "price",
        "created_at",
    )
    list_filter = ("service", "created_at")
    search_fields = (
        "booking__id",
        "service__name",
    )
    readonly_fields = ("created_at",)
