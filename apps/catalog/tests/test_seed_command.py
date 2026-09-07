import pytest
from django.core.management import call_command

from apps.catalog.models import (
    Brand,
    Category,
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
    call_command("seed_catalog")
    assert set(Origin.objects.values_list("slug", flat=True)) == {
        "ethiopia", "colombia", "brazil-ethiopia",
    }


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
