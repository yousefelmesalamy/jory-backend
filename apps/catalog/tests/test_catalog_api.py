from decimal import Decimal

import pytest

from apps.catalog.models import Product, ProductType, ProductVariant

pytestmark = pytest.mark.django_db


def test_the_category_list_is_public_and_returns_only_top_level_entries(api_client, category):
    response = api_client.get("/api/categories/")
    assert response.status_code == 200
    names = [entry["name"] for entry in response.data]
    assert names == ["Coffee"]


def test_the_category_list_nests_children(api_client, category):
    response = api_client.get("/api/categories/")
    coffee = response.data[0]
    assert [child["slug"] for child in coffee["children"]] == ["single-origin"]


def test_a_category_can_be_retrieved_by_slug(api_client, category):
    response = api_client.get("/api/categories/single-origin/")
    assert response.status_code == 200
    assert response.data["name"] == "Single Origin"


def test_inactive_categories_are_hidden(api_client, category):
    category.parent.is_active = False
    category.parent.save()
    response = api_client.get("/api/categories/")
    assert response.data == []


def test_the_roaster_list_is_public(api_client, roaster):
    response = api_client.get("/api/roasters/")
    assert response.status_code == 200
    assert response.data["results"][0]["name"] == "Jory Roastery"


def test_a_roaster_can_be_retrieved_by_slug(api_client, roaster):
    response = api_client.get("/api/roasters/jory-roastery/")
    assert response.status_code == 200
    assert response.data["country"] == "Egypt"


def test_the_product_list_is_public_and_paginated(api_client, product):
    response = api_client.get("/api/products/")
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["slug"] == "ethiopia-yirgacheffe"


def test_the_product_list_summarizes_price_sale_and_stock(api_client, product):
    entry = api_client.get("/api/products/").data["results"][0]
    assert entry["price_from"] == "250.00"
    assert entry["is_on_sale"] is False
    assert entry["in_stock"] is True
    assert entry["category"]["slug"] == "single-origin"
    assert entry["roaster"]["slug"] == "jory-roastery"


def test_the_product_list_reports_a_sale_when_a_variant_is_discounted(api_client, product):
    discounted = product.variants.get(sku="JORY-ETH-250")
    discounted.compare_at_price = Decimal("300.00")
    discounted.save()

    entry = api_client.get("/api/products/").data["results"][0]
    assert entry["is_on_sale"] is True
    assert entry["compare_at_price_from"] == "300.00"


def test_the_product_list_has_no_compare_at_price_when_not_on_sale(api_client, product):
    entry = api_client.get("/api/products/").data["results"][0]
    assert entry["compare_at_price_from"] is None


def test_inactive_products_are_hidden(api_client, product):
    product.is_active = False
    product.save()
    assert api_client.get("/api/products/").data["count"] == 0


def test_the_product_detail_includes_variants_and_the_coffee_profile(api_client, product):
    response = api_client.get("/api/products/ethiopia-yirgacheffe/")
    assert response.status_code == 200
    assert response.data["description"]
    assert {v["sku"] for v in response.data["variants"]} == {"JORY-ETH-250", "JORY-ETH-1000"}
    assert response.data["coffee_profile"]["origin"]["slug"] == "ethiopia"
    assert response.data["coffee_profile"]["origin"]["name"] == "Ethiopia"
    assert response.data["coffee_profile"]["process"] == "WASHED"


def test_variant_payloads_expose_the_derived_sale_fields(api_client, product):
    discounted = product.variants.get(sku="JORY-ETH-250")
    discounted.compare_at_price = Decimal("500.00")
    discounted.save()

    response = api_client.get("/api/products/ethiopia-yirgacheffe/")
    payload = next(v for v in response.data["variants"] if v["sku"] == "JORY-ETH-250")
    assert payload["is_on_sale"] is True
    assert payload["discount_percent"] == 50


def test_equipment_detail_has_no_coffee_profile(api_client, equipment_product):
    response = api_client.get("/api/products/hand-grinder/")
    assert response.status_code == 200
    assert response.data["coffee_profile"] is None


def test_an_unknown_product_slug_returns_the_error_envelope(api_client):
    response = api_client.get("/api/products/does-not-exist/")
    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"


def test_the_catalog_offers_no_write_route_but_staff_product_creation(api_client, product):
    # POST is staff-only (see test_product_create.py); everything else stays admin-only.
    assert api_client.post("/api/products/", {"name": "Hacked"}, format="json").status_code == 401
    assert api_client.delete("/api/products/ethiopia-yirgacheffe/").status_code == 405
    assert api_client.put(
        "/api/products/ethiopia-yirgacheffe/", {"name": "Hacked"}, format="json"
    ).status_code == 405


def test_the_product_list_stays_at_a_fixed_query_count(
    api_client, product, category, roaster, django_assert_num_queries
):
    for index in range(5):
        extra = Product.objects.create(
            name=f"Extra {index}", category=category, roaster=roaster, product_type=ProductType.COFFEE
        )
        ProductVariant.objects.create(
            product=extra, sku=f"EXTRA-{index}", label="250g", price=Decimal("100.00"), stock_quantity=1
        )

    # One count + one page query + one prefetch each for variants and images.
    with django_assert_num_queries(4):
        response = api_client.get("/api/products/")
    assert response.data["count"] == 6
