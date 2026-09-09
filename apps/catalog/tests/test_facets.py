import pytest

from apps.catalog.facets import build_facets
from apps.catalog.models import (
    Brand,
    Category,
    CoffeeProfile,
    Flavor,
    HardwareProfile,
    MachineType,
    Origin,
    Product,
    ProductType,
)

pytestmark = pytest.mark.django_db


def keys(facets):
    return [facet["key"] for facet in facets]


def facet(facets, key):
    return next(entry for entry in facets if entry["key"] == key)


@pytest.fixture
def machines():
    return Category.objects.create(
        name="Roasting Machines", product_type=ProductType.ROASTING_MACHINE
    )


def test_coffee_category_offers_bean_attributes(category):
    """The `category` fixture is Coffee > Single Origin, which inherits COFFEE."""
    offered = keys(build_facets(category, "en"))
    assert {"roast", "process", "origin", "flavor", "roaster"} <= set(offered)
    assert "brand" not in offered
    assert "machine_type" not in offered


def test_machine_category_offers_brand_and_machine_type(machines):
    assert {"brand", "machine_type"} <= set(keys(build_facets(machines, "en")))


def test_machine_category_hides_every_coffee_facet(machines):
    """The bug this whole change exists to fix."""
    offered = keys(build_facets(machines, "en"))
    assert "roast" not in offered
    assert "process" not in offered
    assert "origin" not in offered
    assert "flavor" not in offered
    assert "roaster" not in offered


def test_universal_facets_are_offered_to_every_type(machines):
    for scope in (machines, None):
        offered = set(keys(build_facets(scope, "en")))
        assert {"type", "price", "on_sale", "in_stock", "best_selling", "ordering"} <= offered


def test_no_category_falls_back_to_the_universal_set(db):
    offered = keys(build_facets(None, "en"))
    assert "roast" not in offered
    assert "brand" not in offered


def test_brand_options_list_only_brands_stocked_in_the_subtree(machines):
    shop = Category.objects.create(name="Shop Roasters", parent=machines)
    stocked = Brand.objects.create(name="Probat")
    Brand.objects.create(name="Unstocked Brand")
    item = Product.objects.create(
        name="P5", category=shop, product_type=ProductType.ROASTING_MACHINE
    )
    HardwareProfile.objects.create(product=item, brand=stocked)

    values = [option["value"] for option in facet(build_facets(machines, "en"), "brand")["options"]]
    assert values == ["probat"]


def test_flavor_options_list_only_flavors_stocked_in_the_subtree(category):
    stocked = Flavor.objects.create(name="Vanilla")
    Flavor.objects.create(name="Hazelnut")
    item = Product.objects.create(
        name="Vanilla Blend", category=category, product_type=ProductType.COFFEE
    )
    CoffeeProfile.objects.create(
        product=item, origin=Origin.objects.create(name="Brazil"), flavor=stocked
    )

    values = [option["value"] for option in facet(build_facets(category, "en"), "flavor")["options"]]
    assert values == ["vanilla"]


def test_machine_type_options_list_every_choice(machines):
    values = [
        option["value"] for option in facet(build_facets(machines, "en"), "machine_type")["options"]
    ]
    assert values == [choice.value for choice in MachineType]


def test_arabic_locale_translates_group_and_option_labels(machines):
    built = build_facets(machines, "ar")
    assert facet(built, "brand")["label"] == "العلامة التجارية"
    drum = facet(built, "machine_type")["options"][0]
    assert drum["value"] == "DRUM_ROASTER"
    assert drum["label"] == "محمصة أسطوانية"


def test_range_and_boolean_facets_carry_their_kind(db):
    built = build_facets(None, "en")
    assert facet(built, "price")["kind"] == "range"
    assert facet(built, "on_sale")["kind"] == "boolean"
    assert facet(built, "type")["kind"] == "choice"
