from rest_framework import serializers
from services.models import Service
from .models import Plan, Subscription, PlanBenefit
# Removed build_absolute_media_url - using storage backend directly


class PlanBenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanBenefit
        fields = ('id', 'text', 'is_active')


class PlanSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    benefits_list = PlanBenefitSerializer(many=True, read_only=True)
    included_services = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Service.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Plan
        fields = (
            "id",
            "tier",
            "name",
            "slug",
            "description",
            "image",
            "benefits",
            "benefits_list",
            "services",
            "included_services",
            "price",
            "currency",
            "billing_period",
            "included_visits",
            "active",
            "razorpay_plan_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def create(self, validated_data):
        included_services = validated_data.pop('included_services', None)
        plan = super().create(validated_data)
        if included_services is not None:
            plan.included_services.set(included_services)
        return plan

    def update(self, instance, validated_data):
        included_services = validated_data.pop('included_services', None)
        plan = super().update(instance, validated_data)
        if included_services is not None:
            plan.included_services.set(included_services)
        return plan

    def get_image(self, obj):
        """Returns absolute URL from storage backend"""
        try:
            return obj.image.url if obj.image else None
        except Exception:
            return None


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.SerializerMethodField(read_only=True)
    plan_visit_limit = serializers.IntegerField(source="plan.included_visits", read_only=True)
    visits_used = serializers.IntegerField(source="visits_consumed", read_only=True)
    visits_remaining = serializers.SerializerMethodField(read_only=True)
    remaining_visits = serializers.SerializerMethodField(read_only=True)
    is_active = serializers.SerializerMethodField(read_only=True)
    user_name = serializers.SerializerMethodField(read_only=True)
    user_phone = serializers.SerializerMethodField(read_only=True)
    approved_by = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "plan",
            "plan_name",
            "plan_visit_limit",
            "user",
            "user_name",
            "user_phone",
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
            "visits_used",
            "visits_remaining",
            "remaining_visits",
            "approved_by",
            "approved_at",
            "rejection_reason",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "approved_by", "approved_at", "rejection_reason")

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

    def get_visits_remaining(self, obj):
        return self.get_remaining_visits(obj)

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

    def get_approved_by(self, obj):
        return obj.approved_by.username if obj.approved_by else None

    def get_plan_name(self, obj):
        return obj.plan.name if obj.plan else None

    def get_user_name(self, obj):
        return obj.user.username if obj.user else None

    def get_user_phone(self, obj):
        return obj.user.phone_number if obj.user and hasattr(obj.user, 'phone_number') else None