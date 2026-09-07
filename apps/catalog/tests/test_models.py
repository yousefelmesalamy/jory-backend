import pytest

from apps.catalog.models import Category, Origin, ProductType, Roaster

pytestmark = pytest.mark.django_db


def test_category_slug_is_generated_from_the_name():
    category = Category.objects.create(name="Single Origin")
    assert category.slug == "single-origin"


def test_category_slug_can_be_set_explicitly():
    category = Category.objects.create(name="Single Origin", slug="custom-slug")
    assert category.slug == "custom-slug"


def test_category_children_are_reachable_from_the_parent():
    coffee = Category.objects.create(name="Coffee")
    single_origin = Category.objects.create(name="Single Origin", parent=coffee)
    assert list(coffee.children.all()) == [single_origin]


def test_descendant_ids_includes_self_and_every_nested_category():
    coffee = Category.objects.create(name="Coffee")
    single_origin = Category.objects.create(name="Single Origin", parent=coffee)
    ethiopia = Category.objects.create(name="Ethiopia", parent=single_origin)
    other = Category.objects.create(name="Equipment")

    ids = coffee.descendant_ids()
    assert set(ids) == {coffee.id, single_origin.id, ethiopia.id}
    assert other.id not in ids


def test_descendant_ids_of_a_leaf_is_just_itself():
    leaf = Category.objects.create(name="Grinders")
    assert leaf.descendant_ids() == [leaf.id]


def test_roaster_slug_is_generated_and_string_is_the_name():
    roaster = Roaster.objects.create(name="Jory Roastery", country="Egypt")
    assert roaster.slug == "jory-roastery"
    assert str(roaster) == "Jory Roastery"


def test_origin_slug_is_generated_and_string_is_the_name():
    origin = Origin.objects.create(name="Ethiopia")
    assert origin.slug == "ethiopia"
    assert str(origin) == "Ethiopia"


def test_category_effective_type_defaults_to_coffee():
    assert Category.objects.create(name="Misc").effective_product_type == ProductType.COFFEE


def test_category_effective_type_uses_its_own_when_set():
    machines = Category.objects.create(
        name="Roasting Machines", product_type=ProductType.ROASTING_MACHINE
    )
    assert machines.effective_product_type == ProductType.ROASTING_MACHINE


def test_child_category_inherits_its_parent_type():
    """An admin sets three roots, not every child row."""
    machines = Category.objects.create(
        name="Roasting Machines", product_type=ProductType.ROASTING_MACHINE
    )
    shop = Category.objects.create(name="Shop Roasters", parent=machines)
    assert shop.effective_product_type == ProductType.ROASTING_MACHINE


def test_child_category_own_type_overrides_its_parent():
    machines = Category.objects.create(
        name="Roasting Machines", product_type=ProductType.ROASTING_MACHINE
    )
    spares = Category.objects.create(
        name="Spares", parent=machines, product_type=ProductType.ACCESSORY
    )
    assert spares.effective_product_type == ProductType.ACCESSORY
