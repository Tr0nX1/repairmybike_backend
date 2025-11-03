from django.contrib import admin

from .models import Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "currency", "billing_period", "active")
    list_filter = ("billing_period", "active")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("plan", "user", "contact_email", "status", "start_date", "end_date", "auto_renew")
    list_filter = ("status", "auto_renew")
    search_fields = ("contact_email", "plan__name")
    readonly_fields = ("created_at", "updated_at")