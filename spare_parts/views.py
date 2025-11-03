from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    SparePartCategory,
    SparePartBrand,
    SparePart,
    SparePartFitment,
    Cart,
    CartItem,
)
from .serializers import (
    SparePartCategorySerializer,
    SparePartBrandSerializer,
    SparePartListSerializer,
    SparePartDetailSerializer,
    CartSerializer,
    CartAddItemSerializer,
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
    queryset = SparePart.objects.select_related('brand', 'category').all()
    serializer_class = SparePartDetailSerializer

    def list(self, request, *args, **kwargs):
        q = request.query_params.get('q')
        category_id = request.query_params.get('category')
        brand_id = request.query_params.get('brand')
        in_stock = request.query_params.get('in_stock')
        price_min = request.query_params.get('price_min')
        price_max = request.query_params.get('price_max')
        vehicle_model_id = request.query_params.get('vehicle_model')

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

        serializer = SparePartListSerializer(qs.distinct(), many=True)
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