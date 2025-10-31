from django.contrib import admin

from .models import Customer, Booking, BookingService


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "email", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "phone", "email")
    readonly_fields = ("created_at", "updated_at")


class BookingServiceInline(admin.TabularInline):
    model = BookingService
    extra = 0
    readonly_fields = ("price",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "vehicle_model",
        "service_location",
        "appointment_date",
        "appointment_time",
        "total_amount",
        "payment_status",
        "booking_status",
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
