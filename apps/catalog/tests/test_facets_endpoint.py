import pytest

from apps.catalog.models import Category, ProductType

pytestmark = pytest.mark.django_db


def keys(response):
    return [facet["key"] for facet in response.data["facets"]]


@pytest.fixture
def machine_tree():
    parent = Category.objects.create(
        name="Roasting Machines", product_type=ProductType.ROASTING_MACHINE
    )
    return parent, Category.objects.create(name="Shop Roasters", parent=parent)


def test_coffee_category_returns_bean_facets(api_client, category):
    response = api_client.get(f"/api/facets/?category={category.slug}")
    assert response.status_code == 200
    assert response.data["product_type"] == ProductType.COFFEE
    assert {"roast", "process", "origin"} <= set(keys(response))


def test_machine_category_returns_hardware_facets_and_no_bean_facets(api_client, machine_tree):
    parent, _ = machine_tree
    response = api_client.get(f"/api/facets/?category={parent.slug}")
    assert response.data["product_type"] == ProductType.ROASTING_MACHINE
    assert {"brand", "machine_type"} <= set(keys(response))
    assert "roast" not in keys(response)
    assert "process" not in keys(response)


def test_child_category_inherits_its_parents_facets(api_client, machine_tree):
    _, child = machine_tree
    response = api_client.get(f"/api/facets/?category={child.slug}")
    assert response.data["product_type"] == ProductType.ROASTING_MACHINE
    assert "brand" in keys(response)


def test_no_category_returns_the_universal_set(api_client):
    response = api_client.get("/api/facets/")
    assert response.status_code == 200
    assert response.data["product_type"] is None
    assert "roast" not in keys(response)
    assert "type" in keys(response)


def test_unknown_slug_degrades_instead_of_erroring(api_client):
    """Matches filter_category: a browse endpoint should not 404 on a stale slug."""
    response = api_client.get("/api/facets/?category=nonesuch")
    assert response.status_code == 200
    assert response.data["product_type"] is None


def test_inactive_category_is_treated_as_unknown(api_client):
    hidden = Category.objects.create(
        name="Hidden", product_type=ProductType.ROASTING_MACHINE, is_active=False
    )
    response = api_client.get(f"/api/facets/?category={hidden.slug}")
    assert response.data["product_type"] is None


def test_arabic_header_returns_arabic_labels(api_client, machine_tree):
    parent, _ = machine_tree
    response = api_client.get(f"/api/facets/?category={parent.slug}", HTTP_ACCEPT_LANGUAGE="ar")
    brand = next(entry for entry in response.data["facets"] if entry["key"] == "brand")
    assert brand["label"] == "العلامة التجارية"


def test_lang_query_param_also_selects_arabic(api_client, machine_tree):
    parent, _ = machine_tree
    response = api_client.get(f"/api/facets/?category={parent.slug}&lang=ar")
    brand = next(entry for entry in response.data["facets"] if entry["key"] == "brand")
    assert brand["label"] == "العلامة التجارية"
