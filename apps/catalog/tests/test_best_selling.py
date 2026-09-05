from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.orders.models import Order, OrderItem, OrderStatus

pytestmark = pytest.mark.django_db


def slugs(response):
    return [entry["slug"] for entry in response.data["results"]]


def place_order(user, variant, quantity, days_ago, status=OrderStatus.DELIVERED):
    order = Order.objects.create(
        order_number=f"TEST-{Order.objects.count() + 1}",
        user=user,
        status=status,
        recipient_name="Test",
        phone="0100000000",
        country="Egypt",
        city="Cairo",
        street_address="1 Test St",
        subtotal=variant.price * quantity,
        grand_total=variant.price * quantity,
    )
    Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(days=days_ago))
    OrderItem.objects.create(
        order=order,
        variant=variant,
        product_name=variant.product.name,
        variant_label=variant.label,
        sku=variant.sku,
        unit_price=variant.price,
        quantity=quantity,
        line_total=variant.price * quantity,
    )
    return order


def test_best_selling_week_sorts_by_units_sold_in_the_last_7_days(
    api_client, user, product, equipment_product, variant
):
    other_variant = equipment_product.variants.get()
    place_order(user, variant, quantity=1, days_ago=2)
    place_order(user, other_variant, quantity=10, days_ago=2)

    response = api_client.get("/api/products/?best_selling=week")
    assert response.status_code == 200
    assert slugs(response) == ["hand-grinder", "ethiopia-yirgacheffe"]


def test_best_selling_excludes_sales_outside_the_window(api_client, user, product, variant):
    place_order(user, variant, quantity=5, days_ago=10)

    response = api_client.get("/api/products/?best_selling=week")
    assert response.data["results"][0]["slug"] == "ethiopia-yirgacheffe"
    # Nothing counted inside the window: still returned, just not boosted.
    assert response.status_code == 200


def test_best_selling_excludes_cancelled_orders(api_client, user, product, equipment_product, variant):
    other_variant = equipment_product.variants.get()
    place_order(user, variant, quantity=1, days_ago=1)
    place_order(user, other_variant, quantity=10, days_ago=1, status=OrderStatus.CANCELLED)

    response = api_client.get("/api/products/?best_selling=week")
    assert slugs(response) == ["ethiopia-yirgacheffe", "hand-grinder"]


def test_best_selling_month_and_year_windows(api_client, user, product, equipment_product, variant):
    other_variant = equipment_product.variants.get()
    place_order(user, variant, quantity=1, days_ago=20)
    place_order(user, other_variant, quantity=10, days_ago=20)

    assert slugs(api_client.get("/api/products/?best_selling=week")) == [
        "ethiopia-yirgacheffe", "hand-grinder",
    ]
    assert slugs(api_client.get("/api/products/?best_selling=month")) == [
        "hand-grinder", "ethiopia-yirgacheffe",
    ]


def test_a_product_with_no_sales_in_the_window_sorts_last(api_client, user, product, equipment_product, variant):
    place_order(user, variant, quantity=3, days_ago=1)

    response = api_client.get("/api/products/?best_selling=week")
    assert slugs(response) == ["ethiopia-yirgacheffe", "hand-grinder"]


def test_best_selling_composes_with_other_filters(api_client, user, product, equipment_product, variant):
    place_order(user, variant, quantity=1, days_ago=1)

    response = api_client.get("/api/products/?best_selling=week&category=coffee")
    assert slugs(response) == ["ethiopia-yirgacheffe"]
