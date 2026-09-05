import pytest
from django.db import IntegrityError

from apps.wishlist.models import WishlistItem

pytestmark = pytest.mark.django_db


def test_the_same_product_cannot_be_saved_twice(user, product):
    WishlistItem.objects.create(user=user, product=product)
    with pytest.raises(IntegrityError):
        WishlistItem.objects.create(user=user, product=product)


def test_two_users_can_save_the_same_product(user, other_user, product):
    WishlistItem.objects.create(user=user, product=product)
    WishlistItem.objects.create(user=other_user, product=product)
    assert product.wishlisted_by.count() == 2


def test_the_wishlist_requires_authentication(api_client):
    assert api_client.get("/api/wishlist/").status_code == 401


def test_saving_a_product(auth_client, user, product):
    response = auth_client.post("/api/wishlist/", {"product": product.id}, format="json")
    assert response.status_code == 201
    assert response.data["product"]["slug"] == "ethiopia-yirgacheffe"
    assert WishlistItem.objects.filter(user=user, product=product).exists()


def test_saving_the_same_product_again_is_harmless(auth_client, user, product):
    auth_client.post("/api/wishlist/", {"product": product.id}, format="json")
    response = auth_client.post("/api/wishlist/", {"product": product.id}, format="json")

    assert response.status_code == 200
    assert WishlistItem.objects.filter(user=user).count() == 1


def test_the_list_shows_product_details(auth_client, product):
    auth_client.post("/api/wishlist/", {"product": product.id}, format="json")
    entry = auth_client.get("/api/wishlist/").data["results"][0]

    assert entry["product"]["name"] == "Ethiopia Yirgacheffe"
    assert entry["product"]["price_from"] == "250.00"
    assert entry["product"]["in_stock"] is True


def test_the_list_only_shows_my_saved_products(
    auth_client, user, other_user, product, equipment_product
):
    WishlistItem.objects.create(user=user, product=product)
    WishlistItem.objects.create(user=other_user, product=equipment_product)

    response = auth_client.get("/api/wishlist/")
    assert response.data["count"] == 1
    assert response.data["results"][0]["product"]["slug"] == "ethiopia-yirgacheffe"


def test_removing_a_saved_product_by_product_id(auth_client, user, product):
    auth_client.post("/api/wishlist/", {"product": product.id}, format="json")

    response = auth_client.delete(f"/api/wishlist/{product.id}/")
    assert response.status_code == 204
    assert not WishlistItem.objects.filter(user=user).exists()


def test_removing_something_not_saved_is_a_404(auth_client, product):
    assert auth_client.delete(f"/api/wishlist/{product.id}/").status_code == 404


def test_removing_another_users_saved_product_is_a_404(auth_client, other_user, product):
    WishlistItem.objects.create(user=other_user, product=product)

    assert auth_client.delete(f"/api/wishlist/{product.id}/").status_code == 404
    assert WishlistItem.objects.filter(user=other_user).exists()


def test_saving_an_unknown_product_is_refused(auth_client):
    assert auth_client.post("/api/wishlist/", {"product": 999999}, format="json").status_code == 400
