from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Coupon, CouponUsage
from rest_framework import serializers


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at']


class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer

    def get_permissions(self):
        if self.action == 'validate_coupon':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    @action(detail=False, methods=['post'], url_path='validate')
    def validate_coupon(self, request):
        """
        Validate a coupon code without applying it.
        Body: { "code": "PROM010", "amount": 500 }
        """
        code = request.data.get('code')
        booking_amount = request.data.get('amount', 0)
        
        if not code:
            return Response({'error': True, 'message': 'Coupon code is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            coupon = Coupon.objects.get(code__iexact=code)
        except Coupon.DoesNotExist:
            return Response({'error': True, 'message': 'Invalid coupon code'}, status=status.HTTP_404_NOT_FOUND)
            
        is_valid, error_msg = coupon.is_valid(user=request.user if request.user.is_authenticated else None, amount=float(booking_amount))
        
        if not is_valid:
            return Response({'error': True, 'message': error_msg}, status=status.HTTP_400_BAD_REQUEST)
            
        discount_amount = coupon.calculate_discount(float(booking_amount))
        
        return Response({
            'error': False,
            'message': 'Coupon is valid',
            'data': {
                'code': coupon.code,
                'discount_amount': float(discount_amount),
                'new_total': float(booking_amount) - float(discount_amount),
                'discount_type': coupon.discount_type,
                'description': coupon.description
            }
        })
