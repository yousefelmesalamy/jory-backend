from decimal import Decimal

import pytest

from apps.catalog.models import (
    CoffeeProfile,
    Origin,
    Process,
    Product,
    ProductType,
    ProductVariant,
    RoastLevel,
)

pytestmark = pytest.mark.django_db


def slugs(response):
    return {entry["slug"] for entry in response.data["results"]}


def test_search_matches_the_product_name(api_client, product, equipment_product):
    response = api_client.get("/api/products/?search=yirgacheffe")
    assert response.status_code == 200
    assert slugs(response) == {"ethiopia-yirgacheffe"}


def test_search_is_case_insensitive(api_client, product):
    assert slugs(api_client.get("/api/products/?search=YIRGACHEFFE")) == {"ethiopia-yirgacheffe"}


def test_search_matches_the_description(api_client, product, equipment_product):
    assert slugs(api_client.get("/api/products/?search=jasmine")) == {"ethiopia-yirgacheffe"}


def test_search_matches_a_variant_sku(api_client, product, equipment_product):
    assert slugs(api_client.get("/api/products/?search=JORY-ETH-250")) == {"ethiopia-yirgacheffe"}


def test_search_matches_the_products_own_category_name(api_client, product, equipment_product):
    # The user asked for search across categories as well as product names.
    assert slugs(api_client.get("/api/products/?search=grinders")) == {"hand-grinder"}
    assert slugs(api_client.get("/api/products/?search=single origin")) == {"ethiopia-yirgacheffe"}


def test_search_matches_a_parent_category_name(api_client, product, equipment_product):
    # "Coffee" is the parent of "Single Origin" and appears nowhere else on the
    # product; searching a top-level category must still find what's filed below it.
    assert slugs(api_client.get("/api/products/?search=coffee")) == {"ethiopia-yirgacheffe"}
    assert slugs(api_client.get("/api/products/?search=equipment")) == {"hand-grinder"}


def test_search_matches_the_roaster_name(api_client, product, equipment_product):
    assert slugs(api_client.get("/api/products/?search=jory roastery")) == {"ethiopia-yirgacheffe"}


def test_search_matches_the_country_of_origin(api_client, product, equipment_product):
    assert slugs(api_client.get("/api/products/?search=ethiopia")) == {"ethiopia-yirgacheffe"}


def test_search_returns_each_product_once_even_with_several_matching_variants(api_client, product):
    # Both SKUs contain "JORY-ETH"; the join must not duplicate the product.
    response = api_client.get("/api/products/?search=JORY-ETH")
    assert response.data["count"] == 1


def test_search_with_no_match_returns_nothing(api_client, product):
    assert api_client.get("/api/products/?search=zzzznope").data["count"] == 0


def test_a_blank_search_returns_everything(api_client, product, equipment_product):
    assert api_client.get("/api/products/?search=").data["count"] == 2


def test_search_does_not_distort_the_reported_price(api_client, product):
    # Searching a single SKU must not make price_from that SKU's price.
    entry = api_client.get("/api/products/?search=JORY-ETH-1000").data["results"][0]
    assert entry["price_from"] == "250.00"


def test_category_filter_includes_child_categories(api_client, product, equipment_product):
    assert slugs(api_client.get("/api/products/?category=coffee")) == {"ethiopia-yirgacheffe"}


def test_category_filter_accepts_a_leaf_category(api_client, product, equipment_product):
    assert slugs(api_client.get("/api/products/?category=single-origin")) == {"ethiopia-yirgacheffe"}


def test_an_unknown_category_returns_nothing(api_client, product):
    assert api_client.get("/api/products/?category=nope").data["count"] == 0


def test_roaster_filter(api_client, product, equipment_product):
    assert slugs(api_client.get("/api/products/?roaster=jory-roastery")) == {"ethiopia-yirgacheffe"}


def test_type_filter(api_client, product, equipment_product):
    assert slugs(api_client.get("/api/products/?type=EQUIPMENT")) == {"hand-grinder"}


def test_origin_filter(api_client, product, equipment_product):
    assert slugs(api_client.get("/api/products/?origin=ethiopia")) == {"ethiopia-yirgacheffe"}


def test_an_unknown_origin_returns_nothing(api_client, product):
    assert api_client.get("/api/products/?origin=nope").data["count"] == 0


def test_process_and_roast_filters(api_client, product, category, roaster):
    natural = Product.objects.create(
        name="Brazil Natural", category=category, roaster=roaster, product_type=ProductType.COFFEE
    )
    CoffeeProfile.objects.create(
        product=natural,
        origin=Origin.objects.create(name="Brazil"),
        process=Process.NATURAL,
        roast_level=RoastLevel.DARK,
    )
    ProductVariant.objects.create(
        product=natural, sku="BRZ-250", label="250g", price=Decimal("180.00"), stock_quantity=5
    )

    assert slugs(api_client.get("/api/products/?process=NATURAL")) == {"brazil-natural"}
    assert slugs(api_client.get("/api/products/?roast=LIGHT")) == {"ethiopia-yirgacheffe"}


def test_filters_combine(api_client, product, equipment_product):
    response = api_client.get("/api/products/?category=coffee&roaster=jory-roastery&search=ethiopia")
    assert slugs(response) == {"ethiopia-yirgacheffe"}


def test_filters_that_exclude_each_other_return_nothing(api_client, product, equipment_product):
    assert api_client.get("/api/products/?category=equipment&roaster=jory-roastery").data["count"] == 0
