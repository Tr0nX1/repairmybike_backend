import logging
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Sum
from rest_framework import serializers
from .models import ActivityLog, CashMovement, CashReconciliation, CashSession

logger = logging.getLogger(__name__)
User = get_user_model()


def redact_sensitive_fields(data):
    """
    Recursively redact sensitive fields from log metadata.
    Sensitive patterns: token, password, secret, api_key, signature, 
    card_number, cvv, pin, otp, auth
    Returns (cleaned_dict, redaction_occurred)
    """
    if not isinstance(data, dict):
        return data, False

    sensitive_keys = [
        'token', 'password', 'secret', 'api_key', 'signature', 
        'card_number', 'cvv', 'pin', 'otp', 'auth'
    ]
    redacted = data.copy()
    redaction_occurred = False

    for key in list(redacted.keys()):
        # Check if any sensitive keyword is a substring of the key (case-insensitive)
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            if redacted[key] != '***REDACTED***':
                redacted[key] = '***REDACTED***'
                redaction_occurred = True
        elif isinstance(redacted[key], dict):
            # Recursively handle nested dictionaries
            redacted[key], sub_occurred = redact_sensitive_fields(redacted[key])
            if sub_occurred:
                redaction_occurred = True
        elif isinstance(redacted[key], list):
            # Handle lists of dicts
            new_list = []
            for item in redacted[key]:
                if isinstance(item, dict):
                    cleaned_item, list_sub_occurred = redact_sensitive_fields(item)
                    new_list.append(cleaned_item)
                    if list_sub_occurred:
                        redaction_occurred = True
                else:
                    new_list.append(item)
            redacted[key] = new_list

    return redacted, redaction_occurred


class CashSessionSerializer(serializers.ModelSerializer):
# ... (rest of CashSessionSerializer)

    current_balance = serializers.SerializerMethodField()
    staff_username = serializers.CharField(source='staff.username', read_only=True)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True)

    class Meta:
        model = CashSession
        fields = [
            'id',
            'staff',
            'staff_username',
            'date',
            'opening_balance',
            'closing_balance',
            'expected_closing',
            'variance',
            'status',
            'notes',
            'approved_by',
            'approved_by_username',
            'approved_at',
            'current_balance',
        ]
        read_only_fields = ['id', 'approved_by', 'approved_at', 'current_balance']

    def get_current_balance(self, obj):
        totals = obj.movements.values('movement_type').annotate(total=Sum('amount'))
        movement_totals = {
            item['movement_type']: item['total'] or Decimal('0.00')
            for item in totals
        }
        collections = movement_totals.get(CashMovement.TYPE_COLLECTION, Decimal('0.00'))
        adjustments = movement_totals.get(CashMovement.TYPE_ADJUSTMENT, Decimal('0.00'))
        expenses = movement_totals.get(CashMovement.TYPE_EXPENSE, Decimal('0.00'))
        return obj.opening_balance + collections + adjustments - expenses


class StaffUserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    phone = serializers.CharField(source='phone_number', read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'phone', 'is_manager', 'photo_url']

    def get_name(self, obj):
        return obj.get_full_name() or obj.username or obj.email or obj.phone_number or f"Staff #{obj.id}"

    def get_photo_url(self, obj):
        request = self.context.get('request')
        if obj.profile_picture:
            return request.build_absolute_uri(obj.profile_picture.url) if request else obj.profile_picture.url
        return None


class CashMovementSerializer(serializers.ModelSerializer):
    recorded_by_username = serializers.CharField(source='recorded_by.username', read_only=True)
    verified_by_username = serializers.CharField(source='verified_by.username', read_only=True)
    booking_reference = serializers.CharField(source='booking.id', read_only=True)

    class Meta:
        model = CashMovement
        fields = [
            'id',
            'session',
            'movement_type',
            'booking',
            'booking_reference',
            'amount',
            'description',
            'recorded_by',
            'recorded_by_username',
            'recorded_at',
            'verification_status',
            'verified_by',
            'verified_by_username',
            'verified_at',
        ]
        read_only_fields = [
            'id',
            'recorded_by',
            'recorded_at',
            'verification_status',
            'verified_by',
            'verified_at',
        ]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than 0.')
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['recorded_by'] = request.user
        return super().create(validated_data)


class CashReconciliationSerializer(serializers.ModelSerializer):
    reconciled_by_username = serializers.CharField(source='reconciled_by.username', read_only=True)

    class Meta:
        model = CashReconciliation
        fields = [
            'id',
            'session',
            'total_collections',
            'total_expenses',
            'total_adjustments',
            'calculated_closing',
            'actual_closing',
            'variance',
            'reconciled_by',
            'reconciled_by_username',
            'reconciled_at',
        ]
        read_only_fields = ['id', 'variance', 'reconciled_by', 'reconciled_at']

    def validate(self, attrs):
        attrs['variance'] = attrs['actual_closing'] - attrs['calculated_closing']
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['reconciled_by'] = request.user
        return super().create(validated_data)

class ActivityLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()
    user_detail = serializers.SerializerMethodField()
    booking_detail = serializers.SerializerMethodField()
    details = serializers.JSONField(source='metadata', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = [
            'id',
            'user',
            'username',
            'full_name',
            'user_detail',
            'booking_detail',
            'action_type',
            'description',
            'details',
            'metadata',
            'timestamp',
        ]
        read_only_fields = ['id', 'timestamp']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        
        # Redact metadata on read
        if 'metadata' in ret and ret['metadata']:
            redacted_metadata, occurred = redact_sensitive_fields(ret['metadata'])
            ret['metadata'] = redacted_metadata
            if occurred:
                logger.warning(
                    f"PII Redaction occurred during READ for ActivityLog ID: {instance.id}, "
                    f"Action: {instance.action_type}"
                )
        
        # Details is an alias for metadata, so it should also be redacted
        if 'details' in ret and ret['details']:
            redacted_details, _ = redact_sensitive_fields(ret['details'])
            ret['details'] = redacted_details
            
        return ret

    def validate_metadata(self, value):
        """Sanitize metadata on WRITE (create/update)"""
        if value:
            cleaned_metadata, occurred = redact_sensitive_fields(value)
            if occurred:
                logger.warning("PII Redaction occurred during WRITE for ActivityLog metadata")
            return cleaned_metadata
        return value

    def create(self, validated_data):
        # Double-check redaction before saving
        if 'metadata' in validated_data:
            validated_data['metadata'], _ = redact_sensitive_fields(validated_data['metadata'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Double-check redaction before saving
        if 'metadata' in validated_data:
            validated_data['metadata'], _ = redact_sensitive_fields(validated_data['metadata'])
        return super().update(instance, validated_data)

    def get_full_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
        return "System"

    def get_user_detail(self, obj):
        if not obj.user:
            return None
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'full_name': self.get_full_name(obj),
            'email': obj.user.email,
        }

    def get_booking_detail(self, obj):
        from bookings.models import Booking, BookingPart
        from staff.models import CashMovement

        booking = None
        content_object = obj.content_object
        if isinstance(content_object, Booking):
            booking = content_object
        elif isinstance(content_object, BookingPart):
            booking = content_object.booking
        elif isinstance(content_object, CashMovement):
            booking = content_object.booking
        elif obj.metadata.get('booking_id'):
            try:
                booking = Booking.objects.select_related('customer').get(id=obj.metadata['booking_id'])
            except Booking.DoesNotExist:
                booking = None

        if not booking:
            return None

        return {
            'id': booking.id,
            'customer_name': booking.customer.name,
            'customer_phone': booking.customer.phone,
            'booking_status': booking.booking_status,
            'payment_status': booking.payment_status,
            'total_amount': str(booking.total_amount),
        }
