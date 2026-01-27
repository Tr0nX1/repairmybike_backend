from rest_framework import serializers
from .models import Plan, Subscription, PlanBenefit
# Removed build_absolute_media_url - using storage backend directly



class PlanBenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanBenefit
        fields = ("id", "text", "is_active")


class PlanSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    benefits_list = PlanBenefitSerializer(many=True, read_only=True)
    included_services_details = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = (
            "id",
            "tier",
            "name",
            "slug",
            "description",
            "image",
            "benefits",  # Legacy JSON
            "services",  # Legacy JSON
            "benefits_list", # Structured
            "included_services", # IDs
            "included_services_details", # Detailed info
            "original_price",
            "price",
            "discount_price",
            "currency",
            "billing_period",
            "included_visits",
            "active",
            "razorpay_plan_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_image(self, obj):
        """Returns absolute URL from storage backend"""
        try:
            return obj.image.url if obj.image else None
        except Exception:
            return None

    def get_included_services_details(self, obj):
        """Minimal details for included services for UI consumption"""
        return [
            {
                "id": s.id,
                "name": s.name,
                "category": s.service_category.name if s.service_category else None
            }
            for s in obj.included_services.all()
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    plan_details = PlanSerializer(source="plan", read_only=True)
    remaining_visits = serializers.SerializerMethodField(read_only=True)
    is_active = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "plan",
            "plan_name",
            "plan_details",
            "user",
            "contact_email",
            "contact_phone",
            "status",
            "is_active",
            "auto_renew",
            "start_date",
            "end_date",
            "next_billing_date",
            "razorpay_subscription_id",
            "visits_consumed",
            "remaining_visits",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        plan = attrs.get("plan") or getattr(self.instance, "plan", None)
        if plan and not plan.active:
            raise serializers.ValidationError("Selected plan is not active.")
        return attrs

    def validate_contact_phone(self, value):
        if not value:
            return value
        import re
        if not re.match(r'^\+?1?\d{9,15}$', value):
            raise serializers.ValidationError("Invalid phone number format")
        return value

    def create(self, validated_data):
        subscription = Subscription(**validated_data)
        subscription.end_date = subscription.compute_end_date()
        subscription.next_billing_date = subscription.end_date
        subscription.save()
        return subscription

    def get_remaining_visits(self, obj):
        try:
            included = obj.plan.included_visits or 0
            consumed = obj.visits_consumed or 0
            remaining = included - consumed
            return max(0, remaining)
        except Exception:
            return 0

    def get_is_active(self, obj):
        try:
            # Active if not expired and status is not 'expired'
            # If canceled, remains active until end_date passes
            if obj.end_date is None:
                # No end date set yet (recurring or pending start), treat as active unless explicitly expired
                return obj.status != "expired"
            from django.utils import timezone
            return obj.end_date > timezone.now() and obj.status != "expired"
        except Exception:
            return False
