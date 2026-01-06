from rest_framework import serializers

from .models import Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

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
            "services",
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

    def _abs_url(self, url: str):
        from django.conf import settings
        if not url:
            return None
        if url.startswith('http://') or url.startswith('https://'):
            return url
        request = self.context.get('request') if hasattr(self, 'context') else None
        if request:
            try:
                return request.build_absolute_uri(url)
            except Exception:
                pass
        base = getattr(settings, 'MEDIA_URL', '/')
        if base.startswith('http://') or base.startswith('https://'):
            if url.startswith('/'):
                return f"{base.rstrip('/')}{url}"
            return f"{base.rstrip('/')}/{url}"
        return url

    def get_image(self, obj):
        try:
            return self._abs_url(obj.image.url) if obj.image else None
        except Exception:
            return None


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    remaining_visits = serializers.SerializerMethodField(read_only=True)
    is_active = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "plan",
            "plan_name",
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