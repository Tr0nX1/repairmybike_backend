from django.db.models import Q
from django.core.cache import cache
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    SparePartCategory,
    SparePartBrand,
    SparePart,
    SparePartFitment,
    Cart,
    CartItem,
    Order,
    OrderItem,
    UserSavedPart,
    GuestSavedPart,
)
from authentication.permissions import IsGuestOrAuthenticated
from authentication.models import GuestSession
from .serializers import (
    SparePartCategorySerializer,
    SparePartBrandSerializer,
    SparePartListSerializer,
    SparePartDetailSerializer,
    CartSerializer,
    CartAddItemSerializer,
    OrderSerializer,
    ShipmentUpdateSerializer,
    CheckoutSerializer,
    BuyNowSerializer,
    UserSavedPartSerializer,
    GuestSavedPartSerializer,
)


class SparePartCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SparePartCategory.objects.all()
    serializer_class = SparePartCategorySerializer


class SparePartBrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SparePartBrand.objects.all()
    serializer_class = SparePartBrandSerializer

    def list(self, request, *args, **kwargs):
        category_id = request.query_params.get('category')
        qs = self.get_queryset()
        if category_id:
            qs = qs.filter(parts__category_id=category_id).distinct()
        serializer = self.get_serializer(qs, many=True)
        return Response({
            'error': False,
            'message': 'Spare part brands retrieved successfully',
            'data': serializer.data
        })


class SparePartViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SparePart.objects.select_related(
        'brand', 
        'category'
    ).prefetch_related(
        'images'
    ).all()
    serializer_class = SparePartDetailSerializer

    def list(self, request, *args, **kwargs):
        # Build cache key from query params
        q = request.query_params.get('q', '')
        category_id = request.query_params.get('category', '')
        brand_id = request.query_params.get('brand', '')
        in_stock = request.query_params.get('in_stock', '')
        price_min = request.query_params.get('price_min', '')
        price_max = request.query_params.get('price_max', '')
        vehicle_model_id = request.query_params.get('vehicle_model', '')
        
        cache_key = f'spare_parts_{category_id}_{brand_id}_{in_stock}_{price_min}_{price_max}_{vehicle_model_id}_{q}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response({
                'error': False,
                'message': 'Spare parts retrieved successfully',
                'data': cached_data
            })

        qs = self.get_queryset()

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
        if category_id:
            qs = qs.filter(category_id=category_id)
        if brand_id:
            qs = qs.filter(brand_id=brand_id)
        if in_stock in ['true', 'false']:
            qs = qs.filter(in_stock=(in_stock == 'true'))
        if price_min:
            qs = qs.filter(sale_price__gte=price_min)
        if price_max:
            qs = qs.filter(sale_price__lte=price_max)
        if vehicle_model_id:
            qs = qs.filter(fitments__vehicle_model_id=vehicle_model_id)

        serializer = SparePartListSerializer(qs.distinct(), many=True, context={'request': request})
        
        # Cache for 5 minutes (300 seconds) - same as Services
        cache.set(cache_key, serializer.data, 300)
        
        return Response({
            'error': False,
            'message': 'Spare parts retrieved successfully',
            'data': serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'error': False,
            'message': 'Spare part details retrieved successfully',
            'data': serializer.data
        })

    @action(detail=True, methods=['get'])
    def compatibility(self, request, pk=None):
        part = self.get_object()
        fitments = part.fitments.select_related('vehicle_model__vehicle_brand__vehicle_type').all()
        data = [
            {
                'vehicle_model_id': f.vehicle_model.id,
                'model': f.vehicle_model.name,
                'brand': f.vehicle_model.vehicle_brand.name,
                'type': f.vehicle_model.vehicle_brand.vehicle_type.name,
                'notes': f.notes,
            }
            for f in fitments
        ]
        return Response({
            'error': False,
            'message': 'Compatibility list retrieved successfully',
            'data': data
        })


class CartViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]
    
    def _get_or_create_cart(self, session_id, user=None):
        cart, _ = Cart.objects.get_or_create(session_id=session_id, defaults={'user': user})
        return cart

    def list(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({'error': True, 'message': 'session_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        cart = self._get_or_create_cart(session_id, request.user if request.user and request.user.is_authenticated else None)
        serializer = CartSerializer(cart)
        return Response({'error': False, 'message': 'Cart retrieved successfully', 'data': serializer.data})

    @action(detail=False, methods=['post'])
    def add(self, request):
        serializer = CartAddItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data['session_id']
        spare_part_id = serializer.validated_data['spare_part_id']
        quantity = serializer.validated_data['quantity']

        cart = self._get_or_create_cart(session_id, request.user if request.user and request.user.is_authenticated else None)

        try:
            part = SparePart.objects.get(id=spare_part_id, active=True)
        except SparePart.DoesNotExist:
            return Response({'error': True, 'message': 'Spare part not found'}, status=status.HTTP_404_NOT_FOUND)

        item, created = CartItem.objects.get_or_create(
            cart=cart, spare_part=part,
            defaults={'quantity': quantity, 'unit_price': part.sale_price}
        )
        if not created:
            item.quantity += quantity
            item.unit_price = part.sale_price
            item.save()

        cart_serializer = CartSerializer(cart)
        return Response({'error': False, 'message': 'Item added to cart', 'data': cart_serializer.data}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['patch'])
    def update_item(self, request):
        session_id = request.data.get('session_id')
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')
        if not (session_id and item_id and quantity):
            return Response({'error': True, 'message': 'session_id, item_id and quantity are required'}, status=status.HTTP_400_BAD_REQUEST)
        cart = self._get_or_create_cart(session_id)
        try:
            item = cart.items.get(id=item_id)
        except CartItem.DoesNotExist:
            return Response({'error': True, 'message': 'Cart item not found'}, status=status.HTTP_404_NOT_FOUND)
        item.quantity = int(quantity)
        item.save()
        cart_serializer = CartSerializer(cart)
        return Response({'error': False, 'message': 'Cart item updated', 'data': cart_serializer.data})

    @action(detail=False, methods=['delete'])
    def remove_item(self, request):
        session_id = request.query_params.get('session_id')
        item_id = request.query_params.get('item_id')
        if not (session_id and item_id):
            return Response({'error': True, 'message': 'session_id and item_id are required'}, status=status.HTTP_400_BAD_REQUEST)
        cart = self._get_or_create_cart(session_id)
        deleted, _ = cart.items.filter(id=item_id).delete()
        cart_serializer = CartSerializer(cart)
        return Response({'error': False, 'message': 'Item removed' if deleted else 'Item not found', 'data': cart_serializer.data})

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({'error': True, 'message': 'session_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        cart = self._get_or_create_cart(session_id)
        cart.items.all().delete()
        cart_serializer = CartSerializer(cart)
        return Response({'error': False, 'message': 'Cart cleared', 'data': cart_serializer.data})

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data['session_id']
        customer_name = serializer.validated_data['customer_name']
        phone = serializer.validated_data['phone']
        address = serializer.validated_data['address']

        cart = self._get_or_create_cart(session_id, request.user if request.user and request.user.is_authenticated else None)
        items = list(cart.items.select_related('spare_part'))
        if not items:
            return Response({'error': True, 'message': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        amount_total = 0
        for item in items:
            part = item.spare_part
            if not part.active or not part.in_stock or part.stock_qty < item.quantity:
                return Response({'error': True, 'message': 'Insufficient stock for one or more items'}, status=status.HTTP_400_BAD_REQUEST)
            amount_total += item.unit_price * item.quantity

        # Idempotency Check
        idempotency_key = serializer.validated_data.get('idempotency_key')
        if idempotency_key:
            existing_order = Order.objects.filter(idempotency_key=idempotency_key).first()
            if existing_order:
                order_serializer = OrderSerializer(existing_order)
                return Response({
                    'error': False,
                    'message': 'Order retrieved (Idempotent)',
                    'data': order_serializer.data
                }, status=status.HTTP_200_OK)

        # Handle UserAddress Linkage & Snapshotting
        user_address = None
        user_address_id = serializer.validated_data.get('user_address_id')
        if user_address_id:
            from authentication.models import UserAddress
            try:
                user_address = UserAddress.objects.get(id=user_address_id)
                if not serializer.validated_data.get('address_details'):
                    serializer.validated_data['address_details'] = {
                        'full_name': user_address.full_name,
                        'phone_number': user_address.phone_number,
                        'address_type': user_address.address_type,
                        'flat_house_no': user_address.flat_house_no,
                        'area_street': user_address.area_street,
                        'landmark': user_address.landmark,
                        'pincode': user_address.pincode,
                        'town_city': user_address.town_city,
                        'state': user_address.state,
                        'latitude': float(user_address.latitude) if user_address.latitude else None,
                        'longitude': float(user_address.longitude) if user_address.longitude else None,
                    }
                if not address:
                    address = f"{user_address.flat_house_no}, {user_address.area_street}, {user_address.town_city}"
            except UserAddress.DoesNotExist:
                return Response({'error': True, 'message': 'Invalid user address ID'}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.create(
            session_id=session_id,
            user=request.user if request.user and request.user.is_authenticated else None,
            customer_name=customer_name,
            phone=phone,
            address=address,
            shipping_method=serializer.validated_data.get('shipping_method'),
            address_details=serializer.validated_data.get('address_details'),
            amount_total=amount_total,
            currency='INR',
            payment_method='cash',
            payment_status='cash_due',
            status='created',
            user_address=user_address,
            idempotency_key=idempotency_key
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                spare_part=item.spare_part,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            item.spare_part.stock_qty -= item.quantity
            if item.spare_part.stock_qty <= 0:
                item.spare_part.in_stock = False
                item.spare_part.stock_qty = 0
            item.spare_part.save(update_fields=['stock_qty', 'in_stock', 'updated_at'])

        cart.items.all().delete()
        
        # Send confirmation email
        from notifications.utils import EmailService
        EmailService.send_order_confirmation(order)

        order_serializer = OrderSerializer(order)
        return Response({'error': False, 'message': 'Checkout successful. Pay cash on delivery.', 'data': order_serializer.data}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def buy_now(self, request):
        serializer = BuyNowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data['session_id']
        spare_part_id = serializer.validated_data['spare_part_id']
        quantity = serializer.validated_data['quantity']
        customer_name = serializer.validated_data['customer_name']
        phone = serializer.validated_data['phone']
        address = serializer.validated_data['address']

        try:
            part = SparePart.objects.get(id=spare_part_id, active=True)
        except SparePart.DoesNotExist:
            return Response({'error': True, 'message': 'Spare part not found'}, status=status.HTTP_404_NOT_FOUND)

        if not part.in_stock or part.stock_qty < quantity:
            return Response({'error': True, 'message': 'Insufficient stock'}, status=status.HTTP_400_BAD_REQUEST)

        amount_total = part.sale_price * quantity
        
        # Idempotency Check
        idempotency_key = serializer.validated_data.get('idempotency_key')
        if idempotency_key:
            existing_order = Order.objects.filter(idempotency_key=idempotency_key).first()
            if existing_order:
                order_serializer = OrderSerializer(existing_order)
                return Response({
                    'error': False,
                    'message': 'Order retrieved (Idempotent)',
                    'data': order_serializer.data
                }, status=status.HTTP_200_OK)

        # Handle UserAddress Linkage & Snapshotting
        user_address = None
        user_address_id = serializer.validated_data.get('user_address_id')
        if user_address_id:
            from authentication.models import UserAddress
            try:
                user_address = UserAddress.objects.get(id=user_address_id)
                if not serializer.validated_data.get('address_details'):
                    serializer.validated_data['address_details'] = {
                        'full_name': user_address.full_name,
                        'phone_number': user_address.phone_number,
                        'address_type': user_address.address_type,
                        'flat_house_no': user_address.flat_house_no,
                        'area_street': user_address.area_street,
                        'landmark': user_address.landmark,
                        'pincode': user_address.pincode,
                        'town_city': user_address.town_city,
                        'state': user_address.state,
                        'latitude': float(user_address.latitude) if user_address.latitude else None,
                        'longitude': float(user_address.longitude) if user_address.longitude else None,
                    }
                if not address:
                    address = f"{user_address.flat_house_no}, {user_address.area_street}, {user_address.town_city}"
            except UserAddress.DoesNotExist:
                return Response({'error': True, 'message': 'Invalid user address ID'}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.create(
            session_id=session_id,
            user=request.user if request.user and request.user.is_authenticated else None,
            customer_name=customer_name,
            phone=phone,
            address=address,
            shipping_method=serializer.validated_data.get('shipping_method'),
            address_details=serializer.validated_data.get('address_details'),
            amount_total=amount_total,
            currency='INR',
            payment_method='cash',
            payment_status='cash_due',
            status='created',
            user_address=user_address,
            idempotency_key=idempotency_key
        )

        OrderItem.objects.create(
            order=order,
            spare_part=part,
            quantity=quantity,
            unit_price=part.sale_price,
        )

        part.stock_qty -= quantity
        if part.stock_qty <= 0:
            part.in_stock = False
            part.stock_qty = 0
        part.save(update_fields=['stock_qty', 'in_stock', 'updated_at'])
        
        # Send confirmation email
        from notifications.utils import EmailService
        EmailService.send_order_confirmation(order)

        order_serializer = OrderSerializer(order)
        return Response({'error': False, 'message': 'Order created. Pay cash on delivery.', 'data': order_serializer.data}, status=status.HTTP_201_CREATED)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def list(self, request, *args, **kwargs):
        session_id = request.query_params.get('session_id')
        phone = request.query_params.get('phone')
        qs = self.get_queryset()
        
        # Priority: authenticated user > session_id
        if request.user and request.user.is_authenticated:
            qs = qs.filter(user=request.user)
        elif session_id:
            qs = qs.filter(session_id=session_id)
        else:
            return Response({'error': True, 'message': 'Authentication or session_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(qs.order_by('-created_at'), many=True)
        return Response({'error': False, 'message': 'Orders retrieved successfully', 'data': serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({'error': False, 'message': 'Order details retrieved successfully', 'data': serializer.data})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        instance = self.get_object()
        
        # Check current status
        if instance.status not in ['created', 'pending', 'confirmed']:
            return Response(
                {
                    'error': True,
                    'message': f'Cannot cancel order in {instance.status} status'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if instance.status == 'cancelled':
             return Response(
                {'error': True, 'message': 'Order is already cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Restore stock for each item
        for item in instance.items.all():
            part = item.spare_part
            part.stock_qty += item.quantity
            part.save()

        instance.status = 'cancelled'
        instance.save()
        
        return Response({'success': True, 'message': 'Order cancelled successfully'})

    @action(detail=True, methods=['get'])
    def track(self, request, pk=None):
        """
        Get tracking info and shipment updates for an order.
        """
        instance = self.get_object()
        
        updates = instance.shipment_updates.all()
        serializer = ShipmentUpdateSerializer(updates, many=True)
        
        return Response({
            'error': False,
            'message': 'Tracking info retrieved successfully',
            'data': {
                'id': instance.id,
                'status': instance.status,
                'courier_name': instance.courier_name,
                'tracking_number': instance.tracking_number,
                'courier_tracking_url': instance.courier_tracking_url,
                'estimated_delivery': instance.estimated_delivery,
                'shipped_at': instance.shipped_at,
                'delivered_at': instance.delivered_at,
                'shipment_updates': serializer.data
            }
        })


class SavedPartViewSet(viewsets.ModelViewSet):
    permission_classes = [IsGuestOrAuthenticated]

    def get_serializer_class(self):
        if self.request.user.is_authenticated:
            return UserSavedPartSerializer
        return GuestSavedPartSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return UserSavedPart.objects.filter(user=user)
        
        # Guest User logic
        guest_id = getattr(user, 'guest_id', None)
        if guest_id:
            return GuestSavedPart.objects.filter(guest_session__guest_id=guest_id)
            
        return GuestSavedPart.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'error': False,
            'message': 'Saved parts retrieved',
            'data': serializer.data
        })

    def create(self, request, *args, **kwargs):
        user = request.user
        spare_part_id = request.data.get('spare_part_id')
        
        if not spare_part_id:
             return Response({'error': True, 'message': 'spare_part_id is required'}, status=400)

        if user.is_authenticated:
            saved_obj, created = UserSavedPart.objects.get_or_create(
                user=user, spare_part_id=spare_part_id
            )
            serializer = UserSavedPartSerializer(saved_obj)
        else:
            # Guest Logic
            guest_id = getattr(user, 'guest_id', None)
            guest_session = GuestSession.objects.filter(guest_id=guest_id).first()
            if not guest_session:
                 return Response({'error': True, 'message': 'Invalid guest session'}, status=401)
            
            saved_obj, created = GuestSavedPart.objects.get_or_create(
                guest_session=guest_session, spare_part_id=spare_part_id
            )
            serializer = GuestSavedPartSerializer(saved_obj)

        return Response({
            'error': False,
            'message': 'Part saved successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='remove')
    def remove_part(self, request):
        user = request.user
        spare_part_id = request.data.get('spare_part_id')
        
        if user.is_authenticated:
            deleted, _ = UserSavedPart.objects.filter(
                user=user, spare_part_id=spare_part_id
            ).delete()
        else:
            guest_id = getattr(user, 'guest_id', None)
            deleted, _ = GuestSavedPart.objects.filter(
                guest_session__guest_id=guest_id, spare_part_id=spare_part_id
            ).delete()
        
        return Response({
            'error': False,
            'message': 'Part removed' if deleted else 'Part not found in saved',
        })
