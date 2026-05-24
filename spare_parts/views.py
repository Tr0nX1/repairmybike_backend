from django.db.models import Q
from django.db import transaction
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import (
    SparePartCategory,
    SparePartBrand,
    SparePart,
    SparePartImage,
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
    SparePartImageSerializer,
    CartSerializer,
    CartAddItemSerializer,
    OrderSerializer,
    OrderTransitionSerializer,
    OrderCashPaymentSerializer,
    CheckoutSerializer,
    BuyNowSerializer,
    UserSavedPartSerializer,
    GuestSavedPartSerializer,
)
from staff.models import ActivityLog


class IsOrderOwner(permissions.BasePermission):
    """
    Permission to check if user owns the order or is staff/admin.
    - Authenticated users can only access their own orders
    - Guest users can only access orders with their session_id
    - Staff/Admin can access all orders
    """
    
    def has_object_permission(self, request, view, obj):
        # Staff and admins have full access
        if request.user and (request.user.is_staff or request.user.is_superuser):
            return True
        
        # Authenticated users can only access their own orders
        if request.user and request.user.is_authenticated:
            return obj.user_id == request.user.id
        
        # Guest users can only access orders matching their session
        if getattr(request.user, 'is_guest', False):
            session_id = getattr(request.user, 'session_id', None)
            return session_id and obj.session_id == session_id
        
        return False


class SparePartCategoryViewSet(viewsets.ModelViewSet):
    queryset = SparePartCategory.objects.all()
    serializer_class = SparePartCategorySerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]


class SparePartBrandViewSet(viewsets.ModelViewSet):
    queryset = SparePartBrand.objects.all()
    serializer_class = SparePartBrandSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

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


class SparePartViewSet(viewsets.ModelViewSet):
    queryset = SparePart.objects.select_related('brand', 'category').all()
    serializer_class = SparePartDetailSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'compatibility']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), permissions.IsAdminUser()]

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

        serializer = SparePartListSerializer(qs.distinct(), many=True, context={'request': request})
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

    def perform_create(self, serializer):
        thumbnail = self.request.FILES.get('thumbnail')
        instance = serializer.save(thumbnail=thumbnail) if thumbnail else serializer.save()
        
        ActivityLog.objects.create(
            user=self.request.user,
            action_type='staff_created',
            description=f"Spare part {instance.name} created",
            content_object=instance
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        old_stock = instance.stock_qty
        old_price = instance.sale_price
        
        thumbnail = self.request.FILES.get('thumbnail')
        if thumbnail:
             updated_instance = serializer.save(thumbnail=thumbnail)
        else:
             updated_instance = serializer.save()
        
        # LOG STOCK UPDATE
        if 'stock_qty' in serializer.validated_data:
            new_stock = serializer.validated_data['stock_qty']
            if old_stock != new_stock:
                ActivityLog.objects.create(
                    user=self.request.user,
                    action_type='stock_update',
                    description=f"Stock for {updated_instance.name} updated from {old_stock} to {new_stock}",
                    content_object=updated_instance,
                    metadata={'old_stock': old_stock, 'new_stock': new_stock}
                )
                
        # LOG PRICE UPDATE
        if 'sale_price' in serializer.validated_data:
            new_price = float(serializer.validated_data['sale_price'])
            if float(old_price) != new_price:
                ActivityLog.objects.create(
                    user=self.request.user,
                    action_type='price_change',
                    description=f"Price for {updated_instance.name} changed from ₹{old_price} to ₹{new_price}",
                    content_object=updated_instance,
                    metadata={'old_price': float(old_price), 'new_price': new_price}
                )

    @action(detail=True, methods=['post'], url_path='upload-image', permission_classes=[permissions.IsAdminUser])
    def upload_image(self, request, pk=None):
        """Action: POST /api/spare-parts/parts/<id>/upload-image/"""
        part = self.get_object()
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({'error': True, 'message': 'No image file provided'}, status=400)
        
        is_primary = request.data.get('is_primary', 'false').lower() == 'true'
        
        if is_primary:
            # Unset other primary images
            part.images.filter(is_primary=True).update(is_primary=False)
            
        new_image = SparePartImage.objects.create(
            spare_part=part,
            image=image_file,
            is_primary=is_primary,
            alt_text=request.data.get('alt_text', '')
        )
        
        serializer = SparePartImageSerializer(new_image, context={'request': request})
        return Response({
            'error': False,
            'message': 'Image uploaded to gallery',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='images/(?P<image_id>[^/.]+)', permission_classes=[permissions.IsAdminUser])
    def delete_image(self, request, pk=None, image_id=None):
        """Action: DELETE /api/spare-parts/parts/<id>/images/<image_id>/"""
        part = self.get_object()
        try:
            image = part.images.get(id=image_id)
            image.delete()
            return Response({'error': False, 'message': 'Image removed from gallery'}, status=status.HTTP_200_OK)
        except SparePartImage.DoesNotExist:
            return Response({'error': True, 'message': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)

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

    @action(detail=False, methods=['post'], url_path='bulk-upload', permission_classes=[permissions.IsAdminUser])
    def bulk_upload(self, request):
        """
        Bulk upload/upsert spare parts via CSV.
        Expected columns: name, category_slug, brand_slug, sku, mrp, sale_price, stock_qty, description
        """
        import csv
        import io
        from decimal import Decimal, InvalidOperation

        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({'error': True, 'message': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        if not csv_file.name.endswith('.csv'):
            return Response({'error': True, 'message': 'File is not a CSV'}, status=status.HTTP_400_BAD_REQUEST)

        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)

        # Expected columns validation
        required_cols = ['name', 'category_slug', 'brand_slug', 'sku', 'mrp', 'sale_price', 'stock_qty']
        for col in required_cols:
            if col not in reader.fieldnames:
                return Response({
                    'error': True, 
                    'message': f'Missing required column: {col}'
                }, status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        updated_count = 0
        errors = []

        with transaction.atomic():
            for row_idx, row in enumerate(reader, start=2):
                try:
                    sku = row['sku'].strip()
                    if not sku:
                        raise ValueError("SKU is required")

                    # Basic numeric validation
                    mrp = Decimal(row['mrp'])
                    sale_price = Decimal(row['sale_price'])
                    stock_qty = int(row['stock_qty'])

                    if mrp < 0 or sale_price < 0:
                        raise ValueError("Prices cannot be negative")
                    if stock_qty < 0:
                        raise ValueError("Stock quantity cannot be negative")

                    # Look up category and brand by slug
                    try:
                        category = SparePartCategory.objects.get(slug=row['category_slug'].strip())
                        brand = SparePartBrand.objects.get(slug=row['brand_slug'].strip())
                    except SparePartCategory.DoesNotExist:
                        raise ValueError(f"Category slug '{row['category_slug']}' not found")
                    except SparePartBrand.DoesNotExist:
                        raise ValueError(f"Brand slug '{row['brand_slug']}' not found")

                    # Upsert logic
                    part, created = SparePart.objects.update_or_create(
                        sku=sku,
                        defaults={
                            'name': row['name'].strip(),
                            'category': category,
                            'brand': brand,
                            'mrp': mrp,
                            'sale_price': sale_price,
                            'stock_qty': stock_qty,
                            'description': row.get('description', '').strip(),
                            'slug': sku.lower(), # Fallback slug if needed, usually sku is unique
                        }
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                except (ValueError, InvalidOperation, Exception) as e:
                    errors.append({'row': row_idx, 'error': str(e)})
                    # Optional: transaction.set_rollback(True) if we want "all or nothing"
                    # But the prompt says "if ANY row fails validation, reject entire upload"
                    transaction.set_rollback(True)
                    return Response({
                        'error': True,
                        'message': 'Bulk upload failed due to row errors',
                        'row_errors': errors
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Log the successful batch
            ActivityLog.objects.create(
                user=request.user,
                action_type='bulk_import',
                description=f"Bulk imported spare parts: {created_count} created, {updated_count} updated",
                metadata={'created': created_count, 'updated': updated_count}
            )

        return Response({
            'error': False,
            'message': 'Bulk upload completed successfully',
            'data': {
                'created': created_count,
                'updated': updated_count,
            }
        }, status=status.HTTP_201_CREATED)


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
        serializer = CartSerializer(cart, context={'request': request})
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

        cart_serializer = CartSerializer(cart, context={'request': request})
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
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response({'error': False, 'message': 'Cart item updated', 'data': cart_serializer.data})

    @action(detail=False, methods=['delete'])
    def remove_item(self, request):
        session_id = request.query_params.get('session_id')
        item_id = request.query_params.get('item_id')
        if not (session_id and item_id):
            return Response({'error': True, 'message': 'session_id and item_id are required'}, status=status.HTTP_400_BAD_REQUEST)
        cart = self._get_or_create_cart(session_id)
        deleted, _ = cart.items.filter(id=item_id).delete()
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response({'error': False, 'message': 'Item removed' if deleted else 'Item not found', 'data': cart_serializer.data})

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({'error': True, 'message': 'session_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        cart = self._get_or_create_cart(session_id)
        cart.items.all().delete()
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response({'error': False, 'message': 'Cart cleared', 'data': cart_serializer.data})

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """
        Secure checkout with transaction atomicity and inventory locking.
        Validates all items before processing, prevents race conditions and overselling.
        """
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

        with transaction.atomic():
            # Lock all spare parts in the cart to prevent concurrent modifications
            spare_part_ids = [item.spare_part_id for item in items]
            locked_parts = {
                part.id: part for part in SparePart.objects.filter(id__in=spare_part_ids).select_for_update()
            }
            
            # Validate stock for ALL items before processing ANY
            out_of_stock_items = []
            for item in items:
                part = locked_parts.get(item.spare_part_id)
                if not part:
                    out_of_stock_items.append({
                        'part_name': item.spare_part.name,
                        'requested': item.quantity,
                        'available': 0
                    })
                elif not part.active or not part.in_stock or part.stock_qty < item.quantity:
                    out_of_stock_items.append({
                        'part_name': part.name,
                        'requested': item.quantity,
                        'available': max(0, part.stock_qty) if part.in_stock else 0
                    })
            
            # If any item has insufficient stock, return error without processing
            if out_of_stock_items:
                items_detail = '; '.join([
                    f"{item['part_name']} (requested: {item['requested']}, available: {item['available']})"
                    for item in out_of_stock_items
                ])
                return Response({
                    'error': True,
                    'message': f'Insufficient stock for: {items_detail}',
                    'out_of_stock_items': out_of_stock_items
                }, status=status.HTTP_400_BAD_REQUEST)

            # Calculate total amount
            amount_total = 0
            for item in items:
                amount_total += item.unit_price * item.quantity

            # Create order
            order = Order.objects.create(
                session_id=session_id,
                user=request.user if request.user and request.user.is_authenticated else None,
                customer_name=customer_name,
                phone=phone,
                address=address,
                amount_total=amount_total,
                currency='INR',
                payment_method='cash',
                payment_status='cash_due',
                status='created',
            )

            # Deduct stock ONLY after all validation passes
            for item in items:
                part = locked_parts[item.spare_part_id]
                
                OrderItem.objects.create(
                    order=order,
                    spare_part=part,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                )
                
                # Deduct stock
                part.stock_qty -= item.quantity
                if part.stock_qty < 0:
                    part.stock_qty = 0
                part.save(update_fields=['stock_qty', 'updated_at'])

            # Clear cart after successful checkout
            cart.items.all().delete()

            # Notify staff of new order
            def notify_staff_new_order():
                try:
                    from django.contrib.auth import get_user_model
                    from notifications.models import Notification
                    from repairmybike.fcm import send_push_to_multiple
                    from staff.models import ActivityLog
                    from django.db.models import Q
                    User = get_user_model()
                    
                    staff_users = User.objects.filter(
                        is_active=True
                    ).filter(
                        Q(is_staff=True) |
                        Q(is_manager=True) |
                        Q(is_superuser=True)
                    )
                    
                    item_count = order.items.count()
                    title = f"New Parts Order #{order.id}"
                    body = (
                        f"{order.customer_name} ordered "
                        f"{item_count} item(s). "
                        f"Total: ₹{order.amount_total}"
                    )
                    data = {
                        'type': 'new_order',
                        'order_id': str(order.id),
                    }
                    
                    # DB Notification rows
                    for staff_member in staff_users:
                        Notification.objects.create(
                            user=staff_member,
                            title=title,
                            message=body,
                            notification_type='order_update'
                        )
                    
                    # Push notification
                    send_push_to_multiple(staff_users, title, body, data)
                    
                    # ActivityLog
                    ActivityLog.objects.create(
                        user=order.user,
                        action_type='order_placed',
                        description=f"New order #{order.id} placed "
                                    f"by {order.customer_name}",
                        metadata={
                            'order_id': str(order.id),
                            'amount': str(order.amount_total),
                            'item_count': item_count,
                            'phone': order.phone,
                        }
                    )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(
                        f"Failed to notify staff of new order: {e}"
                    )
            
            transaction.on_commit(notify_staff_new_order)

            order_serializer = OrderSerializer(order, context={'request': request})
            return Response({
                'error': False,
                'message': 'Checkout successful. Pay cash on delivery.',
                'data': order_serializer.data
            }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def buy_now(self, request):
        """
        Secure buy_now with transaction atomicity and inventory locking.
        Validates stock before creating order, prevents race conditions.
        """
        serializer = BuyNowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data['session_id']
        spare_part_id = serializer.validated_data['spare_part_id']
        quantity = serializer.validated_data['quantity']
        customer_name = serializer.validated_data['customer_name']
        phone = serializer.validated_data['phone']
        address = serializer.validated_data['address']

        with transaction.atomic():
            try:
                # Lock the spare part to prevent concurrent modifications
                part = SparePart.objects.select_for_update().get(id=spare_part_id, active=True)
            except SparePart.DoesNotExist:
                return Response({'error': True, 'message': 'Spare part not found'}, status=status.HTTP_404_NOT_FOUND)

            # Validate stock availability
            if not part.in_stock or part.stock_qty < quantity:
                return Response({
                    'error': True,
                    'message': f'Insufficient stock for {part.name}. Available: {max(0, part.stock_qty) if part.in_stock else 0}, Requested: {quantity}',
                    'out_of_stock_item': {
                        'part_name': part.name,
                        'requested': quantity,
                        'available': max(0, part.stock_qty) if part.in_stock else 0
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            # Calculate order total
            amount_total = part.sale_price * quantity
            
            # Create order
            order = Order.objects.create(
                session_id=session_id,
                user=request.user if request.user and request.user.is_authenticated else None,
                customer_name=customer_name,
                phone=phone,
                address=address,
                amount_total=amount_total,
                currency='INR',
                payment_method='cash',
                payment_status='cash_due',
                status='created',
            )

            # Create order item
            OrderItem.objects.create(
                order=order,
                spare_part=part,
                quantity=quantity,
                unit_price=part.sale_price,
            )

            # Deduct stock
            part.stock_qty -= quantity
            if part.stock_qty < 0:
                part.stock_qty = 0
            part.save(update_fields=['stock_qty', 'updated_at'])

            # Notify staff of new order
            def notify_staff_new_order():
                try:
                    from django.contrib.auth import get_user_model
                    from notifications.models import Notification
                    from repairmybike.fcm import send_push_to_multiple
                    from staff.models import ActivityLog
                    from django.db.models import Q
                    User = get_user_model()
                    
                    staff_users = User.objects.filter(
                        is_active=True
                    ).filter(
                        Q(is_staff=True) |
                        Q(is_manager=True) |
                        Q(is_superuser=True)
                    )
                    
                    item_count = order.items.count()
                    title = f"New Parts Order #{order.id}"
                    body = (
                        f"{order.customer_name} ordered "
                        f"{item_count} item(s). "
                        f"Total: ₹{order.amount_total}"
                    )
                    data = {
                        'type': 'new_order',
                        'order_id': str(order.id),
                    }
                    
                    # DB Notification rows
                    for staff_member in staff_users:
                        Notification.objects.create(
                            user=staff_member,
                            title=title,
                            message=body,
                            notification_type='order_update'
                        )
                    
                    # Push notification
                    send_push_to_multiple(staff_users, title, body, data)
                    
                    # ActivityLog
                    ActivityLog.objects.create(
                        user=order.user,
                        action_type='order_placed',
                        description=f"New order #{order.id} placed "
                                    f"by {order.customer_name}",
                        metadata={
                            'order_id': str(order.id),
                            'amount': str(order.amount_total),
                            'item_count': item_count,
                            'phone': order.phone,
                        }
                    )
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(
                        f"Failed to notify staff of new order: {e}"
                    )
            
            transaction.on_commit(notify_staff_new_order)

            order_serializer = OrderSerializer(order, context={'request': request})
            return Response({
                'error': False,
                'message': 'Order created. Pay cash on delivery.',
                'data': order_serializer.data
            }, status=status.HTTP_201_CREATED)


class OrderViewSet(viewsets.ModelViewSet):
    """
    OrderViewSet with IDOR protection.
    - Users can only view/cancel their own orders
    - Guests can only view orders from their session
    - Staff can access all orders
    """
    queryset = Order.objects.prefetch_related('items__spare_part').all()
    serializer_class = OrderSerializer
    ORDER_TRANSITIONS = {
        'created': ['confirmed', 'cancelled'],
        'confirmed': ['fulfilled', 'cancelled'],
        'fulfilled': [],
        'cancelled': [],
    }
    
    def get_permissions(self):
        """
        Assign permissions based on action:
        - list/retrieve: Requires IsAuthenticated
        - update/delete/transition/cash payment collection: Requires IsAuthenticated + IsSuperuserOrManager
        - create/cancel: Requires IsGuestOrAuthenticated + object ownership check (IsOrderOwner)
        """
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        if self.action in ['update', 'partial_update', 'destroy', 'transition_status', 'mark_cash_paid']:
            from staff.permissions import IsSuperuserOrManager
            return [permissions.IsAuthenticated(), IsSuperuserOrManager()]
        return [IsGuestOrAuthenticated(), IsOrderOwner()]
    
    def get_queryset(self):
        """
        Filter orders based on user authentication and role.
        - Authenticated users: only their own orders
        - Guest users: only orders matching their session
        - Staff/Admin: all orders
        """
        user = self.request.user
        
        # Staff and admins see all orders
        if user and (user.is_staff or user.is_superuser):
            return self.queryset.order_by('-created_at')
        
        # Authenticated users see only their orders
        if user and user.is_authenticated:
            return self.queryset.filter(user=user).order_by('-created_at')
        
        # Guest users see only orders from their session
        if getattr(user, 'is_guest', False):
            session_id = getattr(user, 'session_id', None)
            if session_id:
                return self.queryset.filter(session_id=session_id).order_by('-created_at')
        
        # No access for unauthenticated/unidentified users
        return Order.objects.none()

    def list(self, request, *args, **kwargs):
        """
        List orders - filtered by get_queryset() based on user role.
        """
        queryset = self.filter_queryset(self.get_queryset())
        status_filter = request.query_params.get('status')
        payment_status = request.query_params.get('payment_status')
        phone = request.query_params.get('phone')
        search = request.query_params.get('search')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        if phone:
            queryset = queryset.filter(phone=phone)
        if search:
            queryset = queryset.filter(
                Q(customer_name__icontains=search) |
                Q(phone__icontains=search) |
                Q(session_id__icontains=search)
            )
        
        if not queryset.exists():
            return Response({
                'error': False,
                'message': 'No orders found',
                'data': []
            })
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'error': False,
            'message': 'Orders retrieved successfully',
            'data': serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific order.
        """
        try:
            instance = self.get_object()
        except Order.DoesNotExist:
            return Response(
                {'error': True, 'message': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        self.check_object_permissions(request, instance)
        
        serializer = self.get_serializer(instance)
        return Response({
            'error': False,
            'message': 'Order details retrieved successfully',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel an order with ownership verification, atomicity, and stock reversal.
        """
        try:
            instance = self.get_object()
        except Order.DoesNotExist:
            return Response(
                {'error': True, 'message': 'Order not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        self.check_object_permissions(request, instance)
        
        if instance.status == 'cancelled':
            return Response(
                {'error': True, 'message': 'Order is already cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if instance.status not in ['created', 'pending', 'confirmed']:
            return Response(
                {'error': True, 'message': f'Cannot cancel order in {instance.status} status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            instance = Order.objects.select_for_update().get(pk=pk)
            
            if instance.status == 'cancelled':
                return Response(
                    {'error': True, 'message': 'Order was already cancelled'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Reverse stock
            order_items = list(instance.items.select_related('spare_part').select_for_update())
            for item in order_items:
                part = SparePart.objects.select_for_update().get(id=item.spare_part_id)
                part.stock_qty += item.quantity
                part.save(update_fields=['stock_qty', 'updated_at'])

            instance.status = 'cancelled'
            instance.save(update_fields=['status', 'updated_at'])
            
            return Response({
                'error': False,
                'message': 'Order cancelled successfully. Stock has been restored.'
            }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='transition-status')
    @transaction.atomic
    def transition_status(self, request, pk=None):
        serializer = OrderTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = Order.objects.select_for_update().prefetch_related('items__spare_part').get(pk=self.get_object().pk)
        old_status = order.status
        new_status = serializer.validated_data['status']
        notes = serializer.validated_data.get('notes', '')

        allowed_statuses = self.ORDER_TRANSITIONS.get(old_status, [])
        if new_status not in allowed_statuses:
            return Response(
                {
                    'error': f'Cannot transition order from {old_status} to {new_status}',
                    'code': 'INVALID_TRANSITION',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status == 'cancelled':
            for item in order.items.select_related('spare_part'):
                part = SparePart.objects.select_for_update().get(id=item.spare_part_id)
                old_stock = part.stock_qty
                part.stock_qty += item.quantity
                # NOTE: Use save(), not update(), so stock-related signals can observe the stock_qty change.
                part.save(update_fields=['stock_qty', 'updated_at'])
                ActivityLog.objects.create(
                    user=request.user,
                    action_type='stock_reversed',
                    description=f"Restored {item.quantity}x {part.name} for cancelled Order #{order.id}",
                    content_object=item,
                    metadata={
                        'order_id': order.id,
                        'order_item_id': item.id,
                        'part_id': part.id,
                        'quantity': item.quantity,
                        'from': old_stock,
                        'to': part.stock_qty,
                        'old_value': old_stock,
                        'new_value': part.stock_qty,
                    }
                )

        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])

        ActivityLog.objects.create(
            user=request.user,
            action_type='order_status_changed',
            description=f"Order #{order.id} status changed from {old_status} to {new_status}",
            content_object=order,
            metadata={
                'from': old_status,
                'to': new_status,
                'notes': notes,
                'order_id': order.id,
            }
        )

        # Capture values for closure before on_commit
        _order_id = order.id
        _order_phone = order.phone
        _order_user = order.user
        _order_customer_name = order.customer_name
        _new_status = new_status

        def notify_customer_order_update():
            try:
                from django.contrib.auth import get_user_model
                from notifications.models import Notification
                from repairmybike.fcm import send_push_notification
                User = get_user_model()
                
                # Find customer
                customer = _order_user
                if not customer and _order_phone:
                    customer = User.objects.filter(
                        phone_number=_order_phone
                    ).first()
                
                if not customer:
                    # Truly anonymous guest — cannot push
                    return
                
                status_messages = {
                    'confirmed': (
                        f"Order #{_order_id} confirmed! "
                        f"We are preparing your parts."
                    ),
                    'fulfilled': (
                        f"Order #{_order_id} is ready! "
                        f"Your parts have been dispatched. 🚀"
                    ),
                    'cancelled': (
                        f"Order #{_order_id} has been cancelled. "
                        f"Contact the shop for more information."
                    ),
                }
                
                message = status_messages.get(_new_status)
                if not message:
                    return  # no notification for this status
                
                title = "Order Update"
                data = {
                    'type': 'order_status',
                    'order_id': str(_order_id),
                    'status': _new_status,
                }
                
                # DB Notification row
                Notification.objects.create(
                    user=customer,
                    title=title,
                    message=message,
                    notification_type='order_update'
                )
                
                # Push notification
                send_push_notification(customer, title, message, data)
                
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Failed to notify customer of order update: {e}"
                )
        
        transaction.on_commit(notify_customer_order_update)

        order = self.get_queryset().get(pk=order.pk)
        return Response({
            'error': False,
            'message': f'Order status updated to {new_status}',
            'data': self.get_serializer(order).data,
        })

    @action(detail=True, methods=['post'], url_path='mark-cash-paid')
    @transaction.atomic
    def mark_cash_paid(self, request, pk=None):
        serializer = OrderCashPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = Order.objects.select_for_update().prefetch_related('items__spare_part').get(pk=self.get_object().pk)
        if order.payment_status == 'cash_paid':
            return Response(
                {'error': 'Order is already marked cash paid', 'code': 'ALREADY_PAID'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if order.status == 'cancelled':
            return Response(
                {'error': 'Cancelled orders cannot be marked cash paid', 'code': 'ORDER_CANCELLED'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount_received = serializer.validated_data['amount_received']
        notes = serializer.validated_data.get('notes', '')
        old_payment_status = order.payment_status
        order.payment_status = 'cash_paid'
        order.save(update_fields=['payment_status', 'updated_at'])

        ActivityLog.objects.create(
            user=request.user,
            action_type='order_cash_collected',
            description=f"Collected cash payment of {amount_received} for Order #{order.id}",
            content_object=order,
            metadata={
                'amount': str(amount_received),
                'notes': notes,
                'from': old_payment_status,
                'to': order.payment_status,
                'old_value': old_payment_status,
                'new_value': order.payment_status,
                'order_id': order.id,
            }
        )

        order = self.get_queryset().get(pk=order.pk)
        return Response({
            'error': False,
            'message': 'Order marked cash paid',
            'data': self.get_serializer(order).data,
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

        if not SparePart.objects.filter(id=spare_part_id, active=True).exists():
            return Response({'error': True, 'message': 'Spare part not found'}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_authenticated:
            saved_obj, created = UserSavedPart.objects.get_or_create(
                user=user, spare_part_id=spare_part_id
            )
            serializer = UserSavedPartSerializer(saved_obj, context={'request': request})
        else:
            guest_id = getattr(user, 'guest_id', None)
            guest_session = GuestSession.objects.filter(guest_id=guest_id).first()
            if not guest_session:
                 return Response({'error': True, 'message': 'Invalid guest session'}, status=401)
            
            saved_obj, created = GuestSavedPart.objects.get_or_create(
                guest_session=guest_session, spare_part_id=spare_part_id
            )
            serializer = GuestSavedPartSerializer(saved_obj, context={'request': request})

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
