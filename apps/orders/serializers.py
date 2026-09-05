from rest_framework import serializers

from apps.accounts.models import Address

from .models import Order, OrderItem

SHIPPING_FIELDS = [
    "recipient_name", "phone", "country", "city", "area", "street_address",
    "postal_code", "notes",
]


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id", "sku", "product_name", "variant_label", "unit_price", "quantity", "line_total",
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    # `placed_at` is the domain name; `created_at` is where it lives. One column,
    # not two to keep in sync.
    placed_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "status", "payment_method", "payment_status",
            "subtotal", "discount_total", "shipping_cost", "grand_total", "voucher_code",
            "placed_at", "items",
        ] + SHIPPING_FIELDS


class CheckoutSerializer(serializers.Serializer):
    """Address only. Every money figure is computed server-side from the cart."""

    address_id = serializers.IntegerField(required=False)

    recipient_name = serializers.CharField(max_length=150, required=False)
    phone = serializers.CharField(max_length=32, required=False)
    country = serializers.CharField(max_length=100, required=False)
    city = serializers.CharField(max_length=100, required=False)
    area = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    street_address = serializers.CharField(max_length=255, required=False)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    REQUIRED_INLINE = ["recipient_name", "phone", "country", "city", "street_address"]

    def validate(self, attrs):
        user = self.context["request"].user

        if attrs.get("address_id"):
            try:
                address = Address.objects.get(pk=attrs["address_id"], user=user)
            except Address.DoesNotExist:
                raise serializers.ValidationError(
                    {"address_id": "No such address on your account."}
                )
            self.address_data = {
                "recipient_name": address.full_name,
                "phone": address.phone,
                "country": address.country,
                "city": address.city,
                "area": address.area,
                "street_address": address.street_address,
                "postal_code": address.postal_code,
                "notes": attrs.get("notes", "") or address.notes,
            }
            return attrs

        missing = [field for field in self.REQUIRED_INLINE if not attrs.get(field)]
        if missing:
            raise serializers.ValidationError(
                {field: "This field is required without an address_id." for field in missing}
            )

        self.address_data = {field: attrs.get(field, "") for field in SHIPPING_FIELDS}
        return attrs
