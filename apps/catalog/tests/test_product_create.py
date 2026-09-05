import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.catalog.models import Category, Product, ProductType

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff_client(staff_user):
    client = APIClient()
    token = RefreshToken.for_user(staff_user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def payload(category):
    return {
        "name": "Yirgacheffe Reserve",
        "short_description": "Floral and bright.",
        "description": "A washed lot from the Gedeo zone.",
        "category": category.name,
        "product_type": ProductType.COFFEE,
    }


def test_staff_can_create_a_product(staff_client, payload, category):
    response = staff_client.post("/api/products/", payload, format="json")

    assert response.status_code == 201
    product = Product.objects.get(id=response.data["id"])
    assert product.name == "Yirgacheffe Reserve"
    assert product.slug == "yirgacheffe-reserve"
    assert product.category == category


def test_the_category_is_given_and_returned_by_name(staff_client, payload):
    response = staff_client.post("/api/products/", payload, format="json")

    assert response.data["category"] == "Single Origin"


def test_an_unknown_category_name_is_rejected(staff_client, payload):
    response = staff_client.post(
        "/api/products/", {**payload, "category": "Teapots"}, format="json"
    )

    assert response.status_code == 400
    assert "category" in response.data["error"]["details"]


def test_an_inactive_category_cannot_be_chosen(staff_client, payload, category):
    Category.objects.filter(id=category.id).update(is_active=False)

    response = staff_client.post("/api/products/", payload, format="json")

    assert response.status_code == 400
    assert "category" in response.data["error"]["details"]


def test_an_ambiguous_category_name_is_rejected_rather_than_guessed(
    staff_client, payload, category
):
    # A second active category with the same name. The slug is unique and derived
    # from the name, so a duplicate name only exists if someone set the slug by hand.
    Category.objects.create(
        name=category.name, slug="single-origin-equipment",
        parent=Category.objects.create(name="Equipment"),
    )

    response = staff_client.post("/api/products/", payload, format="json")

    assert response.status_code == 400
    assert "more than one category" in str(response.data["error"]["details"]["category"])
    assert not Product.objects.filter(name="Yirgacheffe Reserve").exists()


def test_the_slug_may_be_given_explicitly(staff_client, payload):
    response = staff_client.post(
        "/api/products/", {**payload, "slug": "reserve-2026"}, format="json"
    )

    assert response.status_code == 201
    assert response.data["slug"] == "reserve-2026"


def test_a_duplicate_slug_is_rejected(staff_client, payload, product):
    response = staff_client.post(
        "/api/products/", {**payload, "slug": product.slug}, format="json"
    )

    assert response.status_code == 400
    assert "slug" in response.data["error"]["details"]


def test_a_missing_category_is_rejected(staff_client, payload):
    del payload["category"]
    response = staff_client.post("/api/products/", payload, format="json")

    assert response.status_code == 400
    assert "category" in response.data["error"]["details"]
    assert not Product.objects.filter(name="Yirgacheffe Reserve").exists()


def test_a_signed_in_shopper_cannot_create_a_product(auth_client, payload):
    response = auth_client.post("/api/products/", payload, format="json")

    assert response.status_code == 403
    assert not Product.objects.filter(name="Yirgacheffe Reserve").exists()


def test_an_anonymous_visitor_cannot_create_a_product(api_client, payload):
    response = api_client.post("/api/products/", payload, format="json")

    assert response.status_code == 401
    assert not Product.objects.filter(name="Yirgacheffe Reserve").exists()


def test_browsing_stays_public(api_client, product):
    assert api_client.get("/api/products/").status_code == 200
    assert api_client.get(f"/api/products/{product.slug}/").status_code == 200


def create_property(api_client, name):
    schema = api_client.get("/api/schema/?format=json").data
    return schema["components"]["schemas"]["ProductCreate"]["properties"][name]


def test_the_post_endpoint_is_documented_in_the_schema(api_client):
    schema = api_client.get("/api/schema/?format=json").data

    post = schema["paths"]["/api/products/"]["post"]
    assert post["summary"] == "Create a product"
    properties = schema["components"]["schemas"]["ProductCreate"]["properties"]
    assert {"name", "category", "product_type"} <= set(properties)


def test_the_category_is_documented_as_a_dropdown_of_category_names(api_client, category):
    assert create_property(api_client, "category")["enum"] == ["Coffee", "Single Origin"]


def test_inactive_categories_are_not_offered_in_the_dropdown(api_client, category):
    Category.objects.filter(slug="single-origin").update(is_active=False)

    assert create_property(api_client, "category")["enum"] == ["Coffee"]


def test_a_duplicated_category_name_is_listed_once(api_client, category):
    Category.objects.create(name="Coffee", slug="coffee-nested", parent=category)

    assert create_property(api_client, "category")["enum"] == ["Coffee", "Single Origin"]
