import pytest

from apps.catalog.models import Category, Origin

pytestmark = pytest.mark.django_db


def product_filter_param(api_client, name):
    schema = api_client.get("/api/schema/?format=json").data
    params = schema["paths"]["/api/products/"]["get"]["parameters"]
    return next(param for param in params if param["name"] == name)


def test_the_category_filter_is_documented_as_a_select_of_category_slugs(api_client, category):
    param = product_filter_param(api_client, "category")
    assert set(param["schema"]["enum"]) == {"coffee", "single-origin"}


def test_the_origin_filter_is_documented_as_a_select_of_origin_slugs(api_client, product):
    Origin.objects.create(name="Colombia")
    param = product_filter_param(api_client, "origin")
    assert set(param["schema"]["enum"]) == {"ethiopia", "colombia"}


def test_the_best_selling_filter_is_documented_as_a_select_of_windows(api_client):
    param = product_filter_param(api_client, "best_selling")
    assert set(param["schema"]["enum"]) == {"week", "month", "year"}


def test_inactive_categories_and_origins_are_not_offered_as_options(api_client, category, product):
    Category.objects.filter(slug="single-origin").update(is_active=False)
    Origin.objects.filter(slug="ethiopia").update(is_active=False)

    assert "single-origin" not in product_filter_param(api_client, "category")["schema"]["enum"]
    assert product_filter_param(api_client, "origin")["schema"]["enum"] == []
