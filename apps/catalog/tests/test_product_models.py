from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.catalog.models import (
    Brand,
    Category,
    CoffeeProfile,
    HardwareProfile,
    MachineType,
    Origin,
    Process,
    Product,
    ProductType,
    ProductVariant,
    RoastLevel,
    Roaster,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def coffee_category():
    return Category.objects.create(name="Single Origin")


@pytest.fixture
def catalog_product(coffee_category):
    return Product.objects.create(
        name="Ethiopia Yirgacheffe",
        category=coffee_category,
        product_type=ProductType.COFFEE,
    )


def test_product_slug_is_generated_from_the_name(catalog_product):
    assert catalog_product.slug == "ethiopia-yirgacheffe"


def test_product_rating_defaults_to_zero(catalog_product):
    assert catalog_product.rating_avg == Decimal("0.00")
    assert catalog_product.rating_count == 0


def test_variant_sku_must_be_unique(catalog_product):
    ProductVariant.objects.create(
        product=catalog_product, sku="JORY-ETH-250", label="250g", price=Decimal("250.00")
    )
    with pytest.raises(IntegrityError):
        ProductVariant.objects.create(
            product=catalog_product, sku="JORY-ETH-250", label="1kg", price=Decimal("800.00")
        )


def test_a_variant_without_a_compare_price_is_not_on_sale(catalog_product):
    variant = ProductVariant.objects.create(
        product=catalog_product, sku="JORY-ETH-250", label="250g", price=Decimal("250.00")
    )
    assert variant.is_on_sale is False
    assert variant.discount_percent == 0


def test_a_variant_priced_below_its_compare_price_is_on_sale(catalog_product):
    variant = ProductVariant.objects.create(
        product=catalog_product,
        sku="JORY-ETH-250",
        label="250g",
        price=Decimal("200.00"),
        compare_at_price=Decimal("250.00"),
    )
    assert variant.is_on_sale is True
    assert variant.discount_percent == 20


def test_a_compare_price_at_or_below_the_price_is_rejected_by_the_database(catalog_product):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ProductVariant.objects.create(
                product=catalog_product,
                sku="JORY-ETH-BAD",
                label="250g",
                price=Decimal("250.00"),
                compare_at_price=Decimal("250.00"),
            )


def test_a_negative_price_is_rejected_by_the_database(catalog_product):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ProductVariant.objects.create(
                product=catalog_product, sku="JORY-ETH-NEG", label="250g", price=Decimal("-1.00")
            )


def test_price_from_is_the_cheapest_active_variant(catalog_product):
    ProductVariant.objects.create(product=catalog_product, sku="A", label="1kg", price=Decimal("800.00"))
    ProductVariant.objects.create(product=catalog_product, sku="B", label="250g", price=Decimal("250.00"))
    ProductVariant.objects.create(
        product=catalog_product, sku="C", label="hidden", price=Decimal("10.00"), is_active=False
    )
    assert catalog_product.price_from == Decimal("250.00")


def test_price_from_is_none_when_there_are_no_active_variants(catalog_product):
    assert catalog_product.price_from is None


def test_a_product_is_on_sale_when_any_variant_is(catalog_product):
    ProductVariant.objects.create(product=catalog_product, sku="A", label="1kg", price=Decimal("800.00"))
    assert catalog_product.is_on_sale is False

    ProductVariant.objects.create(
        product=catalog_product,
        sku="B",
        label="250g",
        price=Decimal("200.00"),
        compare_at_price=Decimal("250.00"),
    )
    assert Product.objects.get(pk=catalog_product.pk).is_on_sale is True


def test_compare_at_price_from_is_none_when_the_cheapest_variant_is_not_on_sale(catalog_product):
    ProductVariant.objects.create(product=catalog_product, sku="A", label="250g", price=Decimal("250.00"))
    assert catalog_product.compare_at_price_from is None


def test_compare_at_price_from_is_the_cheapest_variants_original_price(catalog_product):
    ProductVariant.objects.create(
        product=catalog_product,
        sku="A",
        label="250g",
        price=Decimal("200.00"),
        compare_at_price=Decimal("250.00"),
    )
    ProductVariant.objects.create(product=catalog_product, sku="B", label="1kg", price=Decimal("800.00"))
    assert catalog_product.compare_at_price_from == Decimal("250.00")


def test_in_stock_reflects_variant_stock(catalog_product):
    ProductVariant.objects.create(
        product=catalog_product, sku="A", label="250g", price=Decimal("250.00"), stock_quantity=0
    )
    assert Product.objects.get(pk=catalog_product.pk).in_stock is False

    ProductVariant.objects.create(
        product=catalog_product, sku="B", label="1kg", price=Decimal("800.00"), stock_quantity=3
    )
    assert Product.objects.get(pk=catalog_product.pk).in_stock is True


def test_coffee_profile_is_optional_and_reachable(catalog_product):
    assert getattr(catalog_product, "coffee_profile", None) is None

    CoffeeProfile.objects.create(
        product=catalog_product,
        origin=Origin.objects.create(name="Ethiopia"),
        process=Process.WASHED,
        variety="Heirloom",
        roast_level=RoastLevel.LIGHT,
        altitude_masl=1900,
    )
    assert Product.objects.get(pk=catalog_product.pk).coffee_profile.origin.name == "Ethiopia"


def test_equipment_carries_no_coffee_profile(coffee_category):
    grinder = Product.objects.create(
        name="Hand Grinder", category=coffee_category, product_type=ProductType.EQUIPMENT
    )
    assert getattr(grinder, "coffee_profile", None) is None


def test_a_product_can_belong_to_a_roaster(coffee_category):
    brand = Roaster.objects.create(name="Jory Roastery")
    item = Product.objects.create(
        name="House Blend",
        category=coffee_category,
        roaster=brand,
        product_type=ProductType.COFFEE,
    )
    assert list(brand.products.all()) == [item]


def test_brand_slugifies_its_name_on_save():
    assert Brand.objects.create(name="Probat Burns").slug == "probat-burns"


def test_hardware_profile_is_reachable_from_its_product(equipment_category):
    machine = Product.objects.create(
        name="Shop Roaster 5kg",
        category=equipment_category,
        product_type=ProductType.ROASTING_MACHINE,
    )
    brand = Brand.objects.create(name="Probat")
    HardwareProfile.objects.create(
        product=machine, brand=brand, machine_type=MachineType.DRUM_ROASTER
    )
    machine.refresh_from_db()
    assert machine.hardware_profile.brand == brand
    assert machine.hardware_profile.machine_type == MachineType.DRUM_ROASTER


def test_brand_reverses_to_its_hardware_profiles(equipment_category):
    """The facets endpoint walks this reverse name to list stocked brands."""
    brand = Brand.objects.create(name="Giesen")
    machine = Product.objects.create(
        name="W6A", category=equipment_category, product_type=ProductType.ROASTING_MACHINE
    )
    HardwareProfile.objects.create(product=machine, brand=brand)
    assert list(brand.hardware_profiles.all()) == [machine.hardware_profile]


def test_coffee_product_has_no_hardware_profile(product):
    with pytest.raises(HardwareProfile.DoesNotExist):
        product.hardware_profile
