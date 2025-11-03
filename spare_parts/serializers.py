from rest_framework import serializers
from .models import (
    SparePartCategory,
    SparePartBrand,
    SparePart,
    SparePartImage,
    SparePartFitment,
    Cart,
    CartItem,
)


class SparePartCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SparePartCategory
        fields = ['id', 'name', 'slug', 'description', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class SparePartBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = SparePartBrand
        fields = ['id', 'name', 'slug', 'logo', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class SparePartImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SparePartImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'sort_order']
        read_only_fields = ['id']


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
        primary = obj.images.filter(is_primary=True).first()
        return primary.image.url if primary and primary.image else None


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