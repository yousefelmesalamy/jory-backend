from rest_framework import serializers

from apps.catalog.models import ProductVariant
from apps.catalog.serializers import ProductVariantSerializer
from apps.vouchers.models import Voucher

from .models import CartItem


class CartVariantSerializer(ProductVariantSerializer):
    """Variant plus the product identity, so a cart row can be rendered alone."""

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.SlugField(source="product.slug", read_only=True)

    class Meta(ProductVariantSerializer.Meta):
        fields = ProductVariantSerializer.Meta.fields + ["product_name", "product_slug"]


class CartItemSerializer(serializers.ModelSerializer):
    variant = CartVariantSerializer(read_only=True)
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "variant", "quantity", "line_total"]


class CartItemWriteSerializer(serializers.Serializer):
    variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.all())
    quantity = serializers.IntegerField(min_value=1, default=1)


class CartItemQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0)


class VoucherCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=40)


class MergeCartSerializer(serializers.Serializer):
    cart_token = serializers.UUIDField()


class AppliedVoucherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voucher
        fields = ["code", "description", "discount_type", "value"]


class CartSerializer(serializers.Serializer):
    """Read contract. Totals come from the service, never from the client."""

    id = serializers.IntegerField(read_only=True)
    items = CartItemSerializer(many=True, read_only=True)
    voucher = AppliedVoucherSerializer(read_only=True)
    totals = serializers.SerializerMethodField()

    def get_totals(self, obj):
        return {key: str(value) for key, value in self.context["totals"].items()}
