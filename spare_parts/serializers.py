from rest_framework import serializers
from django.conf import settings
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
)


class SparePartCategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = SparePartCategory
        fields = ['id', 'name', 'slug', 'description', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def _abs_url(self, url: str):
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


class SparePartBrandSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()

    class Meta:
        model = SparePartBrand
        fields = ['id', 'name', 'slug', 'logo', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def _abs_url(self, url: str):
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

    def get_logo(self, obj):
        try:
            return self._abs_url(obj.logo.url) if obj.logo else None
        except Exception:
            return None


class SparePartImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = SparePartImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'sort_order']
        read_only_fields = ['id']

    def _abs_url(self, url: str):
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


class SparePartListSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = SparePart
        fields = [
            'id', 'name', 'slug', 'sku', 'brand', 'brand_name', 'category', 'category_name',
            'short_description', 'mrp', 'sale_price', 'currency', 'in_stock', 'stock_qty',
            'warranty_months_total', 'warranty_free_months', 'warranty_pro_rata_months',
            'rating_average', 'rating_count', 'thumbnail', 'created_at', 'updated_at'
        ]

    def _abs_url(self, url: str):
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

    def get_thumbnail(self, obj):
        # Prefer explicitly marked primary image; otherwise fall back to first by sort_order
        primary = obj.images.filter(is_primary=True).first()
        candidate = primary or obj.images.order_by('sort_order').first() or obj.images.first()
        try:
            return self._abs_url(candidate.image.url) if candidate and candidate.image else None
        except Exception:
            return None


class SparePartDetailSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    images = SparePartImageSerializer(many=True, read_only=True)
    fitments = serializers.SerializerMethodField()

    class Meta:
        model = SparePart
        fields = [
            'id', 'name', 'slug', 'sku', 'brand', 'brand_name', 'category', 'category_name',
            'short_description', 'description', 'specs', 'mrp', 'sale_price', 'currency',
            'in_stock', 'stock_qty', 'warranty_months_total', 'warranty_free_months',
            'warranty_pro_rata_months', 'rating_average', 'rating_count', 'weight_grams',
            'length_mm', 'width_mm', 'height_mm', 'images', 'fitments', 'created_at', 'updated_at'
        ]

    def get_fitments(self, obj):
        items = []
        for f in obj.fitments.select_related('vehicle_model__vehicle_brand__vehicle_type').all():
            items.append({
                'vehicle_model_id': f.vehicle_model.id,
                'model': f.vehicle_model.name,
                'brand': f.vehicle_model.vehicle_brand.name,
                'type': f.vehicle_model.vehicle_brand.vehicle_type.name,
                'notes': f.notes,
            })
        return items


class CartItemSerializer(serializers.ModelSerializer):
    part_name = serializers.CharField(source='spare_part.name', read_only=True)
    sku = serializers.CharField(source='spare_part.sku', read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'spare_part', 'part_name', 'sku', 'quantity', 'unit_price', 'total_price']
        read_only_fields = ['id', 'unit_price', 'total_price']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'session_id', 'items', 'total_amount', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CartAddItemSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    spare_part_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class OrderItemSerializer(serializers.ModelSerializer):
    part_name = serializers.CharField(source='spare_part.name', read_only=True)
    sku = serializers.CharField(source='spare_part.sku', read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'spare_part', 'part_name', 'sku', 'quantity', 'unit_price', 'total_price']
        read_only_fields = ['id', 'unit_price', 'total_price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'session_id', 'user', 'customer_name', 'phone', 'address',
            'amount_total', 'currency', 'payment_method', 'payment_status',
            'status', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'amount_total', 'currency', 'payment_method', 'payment_status', 'status', 'created_at', 'updated_at']


class CheckoutSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    customer_name = serializers.CharField()
    phone = serializers.CharField()
    address = serializers.CharField()


class BuyNowSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    spare_part_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    customer_name = serializers.CharField()
    phone = serializers.CharField()
    address = serializers.CharField()
