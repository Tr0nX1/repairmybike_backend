from rest_framework import serializers
from .models import Payment, Refund


class PaymentSerializer(serializers.ModelSerializer):
    total_refunded = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    refundable_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'booking', 'razorpay_order_id', 'razorpay_payment_id',
            'amount', 'currency', 'status', 'payment_method',
            'total_refunded', 'refundable_amount',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RazorpayOrderCreateSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()


class RazorpayPaymentVerifySerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()


class RefundSerializer(serializers.ModelSerializer):
    payment_amount = serializers.DecimalField(
        source='payment.amount', max_digits=10, decimal_places=2, read_only=True
    )
    booking_id = serializers.IntegerField(source='payment.booking_id', read_only=True)
    requested_by_name = serializers.CharField(
        source='requested_by.get_full_name', read_only=True, default=''
    )
    processed_by_name = serializers.CharField(
        source='processed_by.get_full_name', read_only=True, default=''
    )

    class Meta:
        model = Refund
        fields = [
            'id', 'payment', 'booking_id', 'payment_amount',
            'amount', 'currency', 'status',
            'reason', 'reason_detail',
            'razorpay_refund_id',
            'requested_by', 'requested_by_name',
            'processed_by', 'processed_by_name',
            'staff_notes',
            'requested_at', 'processed_at', 'completed_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'requested_at', 'processed_at', 'completed_at', 'updated_at',
            'requested_by', 'processed_by',
        ]


class RefundRequestSerializer(serializers.Serializer):
    """Serializer for requesting a refund."""
    payment_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    reason = serializers.ChoiceField(choices=Refund.REFUND_REASON_CHOICES)
    reason_detail = serializers.CharField(required=False, allow_blank=True, default='')


class RefundProcessSerializer(serializers.Serializer):
    """Serializer for staff processing a refund."""
    action = serializers.ChoiceField(choices=[
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('process', 'Process'),
        ('complete', 'Complete'),
    ])
    staff_notes = serializers.CharField(required=False, allow_blank=True, default='')
    razorpay_refund_id = serializers.CharField(required=False, allow_blank=True, default='')