import pytest
from django.core.management import call_command

from apps.catalog import seed_data
from apps.catalog.management.commands.seed_catalog import PACK_IMAGE
from apps.catalog.models import (
    Brand,
    Category,
    CoffeeProfile,
    HardwareProfile,
    Origin,
    Product,
    ProductType,
    ProductVariant,
    Roaster,
)

pytestmark = pytest.mark.django_db


def test_seeding_creates_the_catalog():
    call_command("seed_catalog")

    assert Category.objects.filter(parent__isnull=True).count() >= 3
    assert Roaster.objects.exists()
    assert Product.objects.filter(product_type=ProductType.COFFEE).exists()
    assert Product.objects.filter(product_type=ProductType.ROASTING_MACHINE).exists()
    assert Product.objects.filter(product_type=ProductType.EQUIPMENT).exists()


def test_every_seeded_product_has_at_least_one_variant():
    call_command("seed_catalog")
    for item in Product.objects.all():
        assert item.variants.exists(), f"{item.name} has no variant"


def test_seeded_coffee_has_an_origin_profile_and_equipment_does_not():
    call_command("seed_catalog")
    coffee = Product.objects.filter(product_type=ProductType.COFFEE).first()
    equipment = Product.objects.filter(product_type=ProductType.EQUIPMENT).first()
    assert coffee.coffee_profile.origin_id
    assert getattr(equipment, "coffee_profile", None) is None


def test_seeding_creates_an_origin_row_per_distinct_origin():
    """Asserted against the dataset rather than a copied-out list, so adding a
    country to seed_data does not silently fail here."""
    call_command("seed_catalog")
    assert set(Origin.objects.values_list("name", flat=True)) == {
        name for name, _ in seed_data.ORIGINS
    }


def test_every_seeded_coffee_carries_the_pack_image_as_its_primary():
    call_command("seed_catalog")
    coffees = Product.objects.filter(product_type=ProductType.COFFEE)
    assert coffees.exists()
    for item in coffees:
        primary = item.primary_image
        assert primary is not None, f"{item.name} has no image"
        assert primary.is_primary
        assert primary.image.name == PACK_IMAGE
        assert item.name in primary.alt_text


def test_hardware_is_not_given_the_coffee_pack_image():
    call_command("seed_catalog")
    for item in Product.objects.exclude(product_type=ProductType.COFFEE):
        assert item.images.count() == 0, f"{item.name} should not carry the coffee pack"


def test_every_seeded_product_is_bilingual():
    call_command("seed_catalog")
    for item in Product.objects.all():
        assert item.name_ar, f"{item.name} has no Arabic name"
        assert item.short_description_ar, f"{item.name} has no Arabic short description"
        assert item.description_ar, f"{item.name} has no Arabic description"


def test_every_seeded_coffee_has_arabic_tasting_notes():
    call_command("seed_catalog")
    for profile in CoffeeProfile.objects.select_related("product"):
        assert profile.tasting_notes, f"{profile.product.name} has no tasting notes"
        assert profile.tasting_notes_ar, f"{profile.product.name} has no Arabic tasting notes"


def test_marked_down_variants_satisfy_the_sale_constraint():
    """compare_at_price is derived in the loader; this proves the derivation
    never lands on or below the price, which the DB would reject."""
    call_command("seed_catalog")
    discounted = ProductVariant.objects.filter(compare_at_price__isnull=False)
    assert discounted.exists()
    for variant in discounted:
        assert variant.compare_at_price > variant.price
        assert variant.is_on_sale
        assert 0 < variant.discount_percent < 100


def test_seeded_skus_are_unique_across_the_catalog():
    call_command("seed_catalog")
    skus = list(ProductVariant.objects.values_list("sku", flat=True))
    assert len(skus) == len(set(skus))


def test_green_beans_are_sold_unground_by_the_kilo():
    call_command("seed_catalog")
    green = Product.objects.get(slug="green-beans-brazil-santos")
    for variant in green.variants.all():
        assert variant.grind == ""
        assert variant.weight_grams >= 1000


def test_seeding_twice_does_not_duplicate_rows():
    call_command("seed_catalog")
    counts = (Category.objects.count(), Product.objects.count(), ProductVariant.objects.count())

    call_command("seed_catalog")
    assert (
        Category.objects.count(),
        Product.objects.count(),
        ProductVariant.objects.count(),
    ) == counts


def test_seed_types_the_root_categories():
    call_command("seed_catalog")
    assert Category.objects.get(name="Coffee").product_type == ProductType.COFFEE
    assert (
        Category.objects.get(name="Roasting Machines").product_type
        == ProductType.ROASTING_MACHINE
    )


def test_seeded_child_category_inherits_its_parent():
    call_command("seed_catalog")
    assert (
        Category.objects.get(name="Shop Roasters").effective_product_type
        == ProductType.ROASTING_MACHINE
    )


def test_seed_gives_every_hardware_product_a_profile():
    call_command("seed_catalog")
    hardware = Product.objects.exclude(product_type=ProductType.COFFEE)
    assert hardware.exists()
    for item in hardware:
        assert item.hardware_profile.brand is not None
        assert item.hardware_profile.machine_type


def test_seed_stays_idempotent_with_brands():
    call_command("seed_catalog")
    call_command("seed_catalog")
    assert Brand.objects.filter(name="Probat").count() == 1
    assert HardwareProfile.objects.count() == Product.objects.exclude(
        product_type=ProductType.COFFEE
    ).count()


def test_seed_corrects_a_root_typed_before_the_field_existed():
    """Re-seeding must fix a blank root, or the machines page keeps offering
    roast filters on an already-seeded database."""
    Category.objects.create(name="Roasting Machines")
    call_command("seed_catalog")
    assert (
        Category.objects.get(name="Roasting Machines", parent=None).product_type
        == ProductType.ROASTING_MACHINE
    )
