from decimal import Decimal

import pytest

from apps.catalog.models import Product, ProductType, ProductVariant

pytestmark = pytest.mark.django_db


def slugs(response):
    return {entry["slug"] for entry in response.data["results"]}


def names_in_order(response):
    return [entry["name"] for entry in response.data["results"]]


@pytest.fixture
def priced_catalog(db, category, roaster):
    """Three coffees at 100 / 300 / 900, the middle one discounted and sold out."""
    made = {}
    rows = [
        ("Cheap Coffee", "CHEAP-1", Decimal("100.00"), None, 5),
        ("Mid Coffee", "MID-1", Decimal("300.00"), Decimal("400.00"), 0),
        ("Pricey Coffee", "PRICEY-1", Decimal("900.00"), None, 2),
    ]
    for name, sku, price, compare_at, stock in rows:
        item = Product.objects.create(
            name=name, category=category, roaster=roaster, product_type=ProductType.COFFEE
        )
        ProductVariant.objects.create(
            product=item,
            sku=sku,
            label="250g",
            price=price,
            compare_at_price=compare_at,
            stock_quantity=stock,
        )
        made[name] = item
    return made


def test_min_price_keeps_products_at_or_above_it(api_client, priced_catalog):
    assert slugs(api_client.get("/api/products/?min_price=300")) == {"mid-coffee", "pricey-coffee"}


def test_max_price_keeps_products_at_or_below_it(api_client, priced_catalog):
    assert slugs(api_client.get("/api/products/?max_price=300")) == {"cheap-coffee", "mid-coffee"}


def test_a_price_range_keeps_only_what_is_inside_it(api_client, priced_catalog):
    assert slugs(api_client.get("/api/products/?min_price=200&max_price=400")) == {"mid-coffee"}


def test_a_range_matching_nothing_returns_nothing(api_client, priced_catalog):
    assert api_client.get("/api/products/?min_price=1000&max_price=2000").data["count"] == 0


def test_a_multi_variant_product_matches_when_any_variant_is_in_range(api_client, product):
    # product has a 250.00 and an 800.00 variant.
    assert api_client.get("/api/products/?min_price=700").data["count"] == 1
    assert api_client.get("/api/products/?max_price=300").data["count"] == 1


def test_on_sale_selects_only_discounted_products(api_client, priced_catalog):
    assert slugs(api_client.get("/api/products/?on_sale=true")) == {"mid-coffee"}


def test_on_sale_false_excludes_discounted_products(api_client, priced_catalog):
    assert slugs(api_client.get("/api/products/?on_sale=false")) == {"cheap-coffee", "pricey-coffee"}


def test_in_stock_excludes_sold_out_products(api_client, priced_catalog):
    assert slugs(api_client.get("/api/products/?in_stock=true")) == {"cheap-coffee", "pricey-coffee"}


def test_inactive_variants_do_not_count_towards_price_or_stock(api_client, category, roaster):
    item = Product.objects.create(
        name="Ghost Deal", category=category, roaster=roaster, product_type=ProductType.COFFEE
    )
    ProductVariant.objects.create(
        product=item, sku="GHOST-1", label="250g", price=Decimal("500.00"), stock_quantity=3
    )
    ProductVariant.objects.create(
        product=item, sku="GHOST-2", label="hidden", price=Decimal("1.00"),
        stock_quantity=99, is_active=False,
    )

    assert api_client.get("/api/products/?max_price=10").data["count"] == 0
    assert api_client.get("/api/products/?min_price=400").data["count"] == 1


def test_ordering_by_price_ascending(api_client, priced_catalog):
    response = api_client.get("/api/products/?ordering=price")
    assert names_in_order(response) == ["Cheap Coffee", "Mid Coffee", "Pricey Coffee"]


def test_ordering_by_price_descending(api_client, priced_catalog):
    response = api_client.get("/api/products/?ordering=-price")
    assert names_in_order(response) == ["Pricey Coffee", "Mid Coffee", "Cheap Coffee"]


def test_ordering_by_name(api_client, priced_catalog):
    assert names_in_order(api_client.get("/api/products/?ordering=name")) == [
        "Cheap Coffee",
        "Mid Coffee",
        "Pricey Coffee",
    ]


def test_ordering_by_rating(api_client, priced_catalog):
    top = priced_catalog["Pricey Coffee"]
    top.rating_avg = Decimal("4.80")
    top.rating_count = 12
    top.save()

    assert names_in_order(api_client.get("/api/products/?ordering=-rating_avg"))[0] == "Pricey Coffee"


def test_ordering_combines_with_filters(api_client, priced_catalog):
    response = api_client.get("/api/products/?in_stock=true&ordering=-price")
    assert names_in_order(response) == ["Pricey Coffee", "Cheap Coffee"]


def test_search_and_facets_combine(api_client, priced_catalog):
    response = api_client.get("/api/products/?search=coffee&min_price=200&ordering=price")
    assert names_in_order(response) == ["Mid Coffee", "Pricey Coffee"]
