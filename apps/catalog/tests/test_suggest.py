from decimal import Decimal

import pytest

from apps.catalog.models import Product, ProductType, ProductVariant

pytestmark = pytest.mark.django_db


def test_suggest_returns_matching_products(api_client, product, equipment_product):
    response = api_client.get("/api/search/suggest/?q=yirga")
    assert response.status_code == 200
    assert [entry["slug"] for entry in response.data["products"]] == ["ethiopia-yirgacheffe"]


def test_suggest_returns_matching_categories(api_client, product, equipment_product):
    response = api_client.get("/api/search/suggest/?q=grind")
    assert [entry["slug"] for entry in response.data["categories"]] == ["grinders"]


def test_suggest_products_carry_a_price(api_client, product):
    entry = api_client.get("/api/search/suggest/?q=yirga").data["products"][0]
    assert entry["price_from"] == "250.00"
    assert entry["product_type"] == "COFFEE"


def test_suggest_requires_a_query(api_client, product):
    response = api_client.get("/api/search/suggest/")
    assert response.status_code == 200
    assert response.data == {"products": [], "categories": []}


def test_a_blank_query_returns_empty_lists(api_client, product):
    assert api_client.get("/api/search/suggest/?q=   ").data == {"products": [], "categories": []}


def test_suggest_returns_at_most_five_products(api_client, category, roaster):
    for index in range(8):
        item = Product.objects.create(
            name=f"Espresso Blend {index}",
            category=category,
            roaster=roaster,
            product_type=ProductType.COFFEE,
        )
        ProductVariant.objects.create(
            product=item, sku=f"ESP-{index}", label="250g",
            price=Decimal("100.00"), stock_quantity=1,
        )

    assert len(api_client.get("/api/search/suggest/?q=espresso").data["products"]) == 5


def test_suggest_hides_inactive_products(api_client, product):
    product.is_active = False
    product.save()
    assert api_client.get("/api/search/suggest/?q=yirga").data["products"] == []


def test_suggest_hides_inactive_categories(api_client, equipment_product):
    equipment_product.category.is_active = False
    equipment_product.category.save()

    response = api_client.get("/api/search/suggest/?q=grinders")
    assert response.data["categories"] == []
    # Deactivating a category retires the category, not the products filed under
    # it — an active product still surfaces, matching the product-list behaviour.
    assert [entry["slug"] for entry in response.data["products"]] == ["hand-grinder"]


def test_suggest_needs_no_authentication(api_client, product):
    assert api_client.get("/api/search/suggest/?q=coffee").status_code == 200
