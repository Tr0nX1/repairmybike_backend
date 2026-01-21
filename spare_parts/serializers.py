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
    UserSavedPart,
    GuestSavedPart,
)
# Removed build_absolute_media_url - using storage backend directly



class SparePartCategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = SparePartCategory
        fields = ['id', 'name', 'slug', 'description', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_image(self, obj):
        """Returns standardized media object"""
        if not obj.image:
            return None
        try:
            url = obj.image.url
            return {
                "thumbnail": url, # Using standard URL for now, Cloudinary presets can be added later
                "original": url,
                "alt_text": obj.name
            }
        except Exception:
            return None


class SparePartBrandSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()

    class Meta:
        model = SparePartBrand
        fields = ['id', 'name', 'slug', 'logo', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_logo(self, obj):
        """Returns standardized media object"""
        if not obj.logo:
            return None
        try:
            url = obj.logo.url
            return {
                "thumbnail": url,
                "original": url,
                "alt_text": obj.name
            }
        except Exception:
            return None


class SparePartImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = SparePartImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'sort_order']
        read_only_fields = ['id']

    def get_image(self, obj):
        """Returns standardized media object"""
        if not obj.image:
            return None
        try:
            url = obj.image.url
            return {
                "thumbnail": url,
                "original": url,
                "alt_text": obj.alt_text or f"Image for {obj.spare_part.name}"
            }
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

    def get_thumbnail(self, obj):
        """Returns standardized media object for the primary image"""
        primary = obj.images.filter(is_primary=True).first()
        candidate = primary or obj.images.order_by('sort_order').first() or obj.images.first()
        if not candidate or not candidate.image:
            return None
        try:
            url = candidate.image.url
            return {
                "thumbnail": url,
                "original": url,
                "alt_text": candidate.alt_text or obj.name
            }
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
    image = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'spare_part', 'part_name', 'sku', 'quantity', 'unit_price', 'total_price', 'image']
        read_only_fields = ['id', 'unit_price', 'total_price']

    def get_image(self, obj):
        """Returns standardized media object for the spare part"""
        if not obj.spare_part:
            return None
        primary = obj.spare_part.images.filter(is_primary=True).first()
        candidate = primary or obj.spare_part.images.order_by('sort_order').first() or obj.spare_part.images.first()
        if not candidate or not candidate.image:
            return None
        try:
            url = candidate.image.url
            return {
                "thumbnail": url,
                "original": url,
                "alt_text": candidate.alt_text or obj.spare_part.name
            }
        except Exception:
            return None


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
    image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'spare_part', 'part_name', 'sku', 'quantity', 'unit_price', 'total_price', 'image']
        read_only_fields = ['id', 'unit_price', 'total_price']

    def get_image(self, obj):
        """Returns standardized media object for the spare part"""
        if not obj.spare_part:
            return None
        primary = obj.spare_part.images.filter(is_primary=True).first()
        candidate = primary or obj.spare_part.images.order_by('sort_order').first() or obj.spare_part.images.first()
        if not candidate or not candidate.image:
            return None
        try:
            url = candidate.image.url
            return {
                "thumbnail": url,
                "original": url,
                "alt_text": candidate.alt_text or obj.spare_part.name
            }
        except Exception:
            return None


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'session_id', 'user', 'customer_name', 'phone', 'address',
            'amount_total', 'currency', 'payment_method', 'payment_status',
            'status', 'items', 'tracking_number', 'courier_name',
            'estimated_delivery', 'delivered_at', 'created_at', 'updated_at'
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

class UserSavedPartSerializer(serializers.ModelSerializer):
    spare_part = SparePartListSerializer(read_only=True)

    class Meta:
        model = UserSavedPart
        fields = ['id', 'spare_part', 'created_at']
        read_only_fields = ['id', 'created_at']


class GuestSavedPartSerializer(serializers.ModelSerializer):
    spare_part = SparePartListSerializer(read_only=True)

    class Meta:
        model = GuestSavedPart
        fields = ['id', 'spare_part', 'created_at']
        read_only_fields = ['id', 'created_at']
