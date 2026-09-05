import pytest
from django.core.management import call_command

from apps.catalog.models import Category, Origin, Product, ProductType, ProductVariant, Roaster

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
