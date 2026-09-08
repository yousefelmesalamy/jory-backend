from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.catalog.models import (
    Category,
    CoffeeProfile,
    Origin,
    Process,
    Product,
    ProductType,
    ProductVariant,
    RoastLevel,
    Roaster,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_password():
    return "StrongPassw0rd!"


@pytest.fixture
def user(db, user_password):
    return get_user_model().objects.create_user(
        email="shopper@example.com",
        password=user_password,
        username="shopper_one",
        full_name="Shopper One",
        phone="+201000000000",
    )


@pytest.fixture
def other_user(db, user_password):
    return get_user_model().objects.create_user(
        email="other@example.com",
        password=user_password,
        username="shopper_two",
        full_name="Shopper Two",
    )


@pytest.fixture
def staff_user(db, user_password):
    return get_user_model().objects.create_superuser(
        email="staff@example.com",
        password=user_password,
        username="staff_member",
        full_name="Staff Member",
    )


@pytest.fixture
def auth_client(user):
    # Its own client, NOT a mutated `api_client`: a test that needs both a guest
    # and a signed-in shopper (cart merge, for one) must get two distinct clients.
    client = APIClient()
    token = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


# --- Catalog fixtures, reused by Phases 4-6 -----------------------------------


@pytest.fixture
def category(db):
    parent = Category.objects.create(name="Coffee")
    return Category.objects.create(name="Single Origin", parent=parent)


@pytest.fixture
def equipment_category(db):
    parent = Category.objects.create(name="Equipment")
    return Category.objects.create(name="Grinders", parent=parent)


@pytest.fixture
def roaster(db):
    return Roaster.objects.create(name="Jory Roastery", country="Egypt")


@pytest.fixture
def origin(db):
    return Origin.objects.create(name="Ethiopia")


@pytest.fixture
def product(db, category, roaster, origin):
    item = Product.objects.create(
        name="Ethiopia Yirgacheffe",
        short_description="Floral and bright.",
        description="A washed Yirgacheffe with jasmine and citrus.",
        category=category,
        roaster=roaster,
        product_type=ProductType.COFFEE,
    )
    CoffeeProfile.objects.create(
        product=item,
        origin=origin,
        region="Yirgacheffe",
        process=Process.WASHED,
        roast_level=RoastLevel.LIGHT,
        altitude_masl=1900,
        tasting_notes="Jasmine, lemon, black tea",
    )
    ProductVariant.objects.create(
        product=item, sku="JORY-ETH-250", label="250g", weight_grams=250,
        price=Decimal("250.00"), stock_quantity=10,
    )
    ProductVariant.objects.create(
        product=item, sku="JORY-ETH-1000", label="1kg", weight_grams=1000,
        price=Decimal("800.00"), stock_quantity=4,
    )
    return item


@pytest.fixture
def variant(product):
    return product.variants.get(sku="JORY-ETH-250")


@pytest.fixture
def equipment_product(db, equipment_category):
    item = Product.objects.create(
        name="Hand Grinder",
        category=equipment_category,
        product_type=ProductType.EQUIPMENT,
    )
    ProductVariant.objects.create(
        product=item, sku="JORY-GRINDER", label="Default",
        price=Decimal("1200.00"), stock_quantity=2,
    )
    return item
