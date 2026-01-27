from django.contrib import admin
from .models import Plan, Subscription, PlanBenefit
from repairmybike.admin_mixins import ImagePreviewMixin



class PlanBenefitInline(admin.TabularInline):
    model = PlanBenefit
    extra = 1


@admin.register(Plan)
class PlanAdmin(ImagePreviewMixin, admin.ModelAdmin):
    list_display = ("name", "price", "discount_price", "currency", "billing_period", "active", "image_preview")
    list_filter = ("billing_period", "active")
    search_fields = ("name", "description")
    readonly_fields = ("image_preview", "created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("included_services",)
    inlines = [PlanBenefitInline]

    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'image', 'tier', 'description', 'active')
        }),
        ('Pricing & Billing', {
            'fields': ('price', 'discount_price', 'currency', 'billing_period', 'included_visits')
        }),
        ('Features (New)', {
            'fields': ('included_services',),
            'description': 'Select services directly from the catalog.'
        }),
        ('Technical ID', {
            'classes': ('collapse',),
            'fields': ('razorpay_plan_id',)
        }),
        ('Legacy Data (JSON)', {
            'classes': ('collapse',),
            'fields': ('benefits', 'services'),
            'description': 'Old fields used before structured improvement.'
        }),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("plan", "user", "contact_email", "status", "start_date", "end_date", "auto_renew")
    list_filter = ("status", "auto_renew")
    search_fields = ("contact_email", "plan__name")
    readonly_fields = ("created_at", "updated_at")
    
    fieldsets = (
        (None, {
            'fields': ('plan', 'user', 'status', 'auto_renew')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone')
        }),
        ('Dates & Cycles', {
            'fields': ('start_date', 'end_date', 'next_billing_date')
        }),
        ('Usage Tracking', {
            'fields': ('visits_consumed',)
        }),
        ('Technical Details', {
            'classes': ('collapse',),
            'fields': ('razorpay_subscription_id', 'metadata')
        }),
    )


@admin.register(PlanBenefit)
class PlanBenefitAdmin(admin.ModelAdmin):
    list_display = ("plan", "text", "is_active", "created_at")
    list_filter = ("plan", "is_active")
    search_fields = ("text",)