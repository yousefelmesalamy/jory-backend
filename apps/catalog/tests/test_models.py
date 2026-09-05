import pytest

from apps.catalog.models import Category, Origin, Roaster

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
