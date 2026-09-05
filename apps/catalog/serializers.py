from apps.core.i18n import get_locale
from rest_framework import serializers

from .models import (
    GRIND_LABELS_AR,
    PROCESS_LABELS_AR,
    PRODUCT_TYPE_LABELS_AR,
    ROAST_LEVEL_LABELS_AR,
    Category,
    CoffeeProfile,
    Origin,
    Product,
    ProductImage,
    ProductVariant,
    Roaster,
)


class LocalizedField(serializers.Field):
    """Reads `<field>` normally, or `<field>_ar` when the request resolves to
    Arabic — falling back to the English value if no translation was entered.
    Requires `context["request"]` (every view here passes it via
    get_serializer_context, which DRF wires up automatically)."""

    def __init__(self, **kwargs):
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    def get_attribute(self, instance):
        return instance

    def to_representation(self, instance):
        base_value = getattr(instance, self.field_name)
        request = self.context.get("request")
        if request is not None and get_locale(request) == "ar":
            ar_value = getattr(instance, f"{self.field_name}_ar", "")
            return ar_value or base_value
        return base_value


class LocalizedChoiceField(serializers.Field):
    """Like LocalizedField, but for TextChoices whose Arabic labels live in a
    lookup dict rather than a database column (name_ar). Always emits the
    English code plus a human-readable label, e.g. {"value": "WASHED",
    "label": "مغسولة"}."""

    def __init__(self, labels_ar, **kwargs):
        self.labels_ar = labels_ar
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    def get_attribute(self, instance):
        return instance

    def to_representation(self, instance):
        code = getattr(instance, self.field_name)
        if not code:
            return {"value": "", "label": ""}
        request = self.context.get("request")
        if request is not None and get_locale(request) == "ar":
            label = self.labels_ar.get(code, code)
        else:
            choices_field = instance._meta.get_field(self.field_name)
            label = dict(choices_field.choices).get(code, code)
        return {"value": code, "label": label}


class CategorySlimSerializer(serializers.ModelSerializer):
    name = LocalizedField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class CategorySerializer(serializers.ModelSerializer):
    name = LocalizedField()
    description = LocalizedField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "image", "display_order", "children"]

    def get_children(self, obj):
        active_children = [child for child in obj.children.all() if child.is_active]
        return CategorySerializer(active_children, many=True, context=self.context).data


class RoasterSlimSerializer(serializers.ModelSerializer):
    name = LocalizedField()

    class Meta:
        model = Roaster
        fields = ["id", "name", "slug"]


class RoasterSerializer(serializers.ModelSerializer):
    name = LocalizedField()
    bio = LocalizedField()

    class Meta:
        model = Roaster
        fields = ["id", "name", "slug", "country", "logo", "bio", "website"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_primary", "display_order"]


class ProductVariantSerializer(serializers.ModelSerializer):
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    grind = LocalizedChoiceField(GRIND_LABELS_AR)

    class Meta:
        model = ProductVariant
        fields = [
            "id", "sku", "label", "weight_grams", "grind", "price", "compare_at_price",
            "stock_quantity", "is_on_sale", "discount_percent", "in_stock",
        ]


class OriginSerializer(serializers.ModelSerializer):
    class Meta:
        model = Origin
        fields = ["id", "name", "slug"]


class CoffeeProfileSerializer(serializers.ModelSerializer):
    origin = OriginSerializer(read_only=True)
    process = LocalizedChoiceField(PROCESS_LABELS_AR)
    roast_level = LocalizedChoiceField(ROAST_LEVEL_LABELS_AR)

    class Meta:
        model = CoffeeProfile
        fields = [
            "origin", "region", "farm", "process", "variety", "roast_level",
            "altitude_masl", "tasting_notes", "harvest_year", "cupping_score",
        ]


class ProductListSerializer(serializers.ModelSerializer):
    name = LocalizedField()
    short_description = LocalizedField()
    product_type = LocalizedChoiceField(PRODUCT_TYPE_LABELS_AR)
    category = CategorySlimSerializer(read_only=True)
    roaster = RoasterSlimSerializer(read_only=True)
    price_from = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    compare_at_price_from = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True, allow_null=True
    )
    is_on_sale = serializers.BooleanField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "short_description", "product_type", "category", "roaster",
            "is_featured", "rating_avg", "rating_count", "price_from", "compare_at_price_from",
            "is_on_sale", "in_stock", "primary_image",
        ]

    def get_primary_image(self, obj):
        image = obj.primary_image
        return ProductImageSerializer(image, context=self.context).data if image else None


class ProductSuggestionSerializer(serializers.ModelSerializer):
    """Deliberately small: a type-ahead row, not a product card."""

    name = LocalizedField()
    price_from = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "slug", "product_type", "price_from"]


class CategoryNameField(serializers.SlugRelatedField):
    """Picks a category by its name so Swagger renders a readable dropdown rather
    than a bare id box. The option list is filled in by `apps.catalog.schema`.

    Category names are not unique in the database, so an ambiguous one is
    rejected instead of resolved arbitrarily.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("slug_field", "name")
        kwargs.setdefault("queryset", Category.objects.filter(is_active=True))
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        matches = list(self.get_queryset().filter(name=data)[:2])
        if not matches:
            self.fail("does_not_exist", slug_name=self.slug_field, value=data)
        if len(matches) > 1:
            raise serializers.ValidationError(
                f'"{data}" is the name of more than one category. Rename one of them, '
                f"or file the product through the admin."
            )
        return matches[0]


class ProductCreateSerializer(serializers.ModelSerializer):
    """Staff-only product creation. Variants, images and the coffee profile are
    attached afterwards through the admin — this writes the catalog entry only."""

    category = CategoryNameField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "name_ar", "slug", "short_description", "short_description_ar",
            "description", "description_ar", "category", "roaster", "product_type",
            "is_active", "is_featured",
        ]
        read_only_fields = ["id"]
        # Omitting the slug is normal: Product.save() derives it from the name.
        extra_kwargs = {"slug": {"required": False}}


class ProductDetailSerializer(ProductListSerializer):
    description = LocalizedField()
    roaster = RoasterSerializer(read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    coffee_profile = CoffeeProfileSerializer(read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            "description", "variants", "images", "coffee_profile",
        ]
