import pytest

from apps.accounts.models import Address

pytestmark = pytest.mark.django_db

PAYLOAD = {
    "full_name": "Shopper One",
    "phone": "+201000000000",
    "country": "Egypt",
    "city": "Cairo",
    "area": "Maadi",
    "street_address": "12 Road 9",
    "postal_code": "11431",
}


def test_creating_an_address_attaches_it_to_the_requesting_user(auth_client, user):
    response = auth_client.post("/api/addresses/", PAYLOAD, format="json")
    assert response.status_code == 201
    assert Address.objects.get(id=response.data["id"]).user == user


def test_addresses_require_authentication(api_client):
    assert api_client.get("/api/addresses/").status_code == 401


def test_the_list_only_returns_the_requesting_users_addresses(auth_client, user, other_user):
    Address.objects.create(user=user, **PAYLOAD)
    Address.objects.create(user=other_user, **PAYLOAD)

    response = auth_client.get("/api/addresses/")
    assert response.status_code == 200
    assert response.data["count"] == 1


def test_a_user_cannot_read_another_users_address(auth_client, other_user):
    foreign = Address.objects.create(user=other_user, **PAYLOAD)
    assert auth_client.get(f"/api/addresses/{foreign.id}/").status_code == 404


def test_a_user_cannot_delete_another_users_address(auth_client, other_user):
    foreign = Address.objects.create(user=other_user, **PAYLOAD)
    assert auth_client.delete(f"/api/addresses/{foreign.id}/").status_code == 404
    assert Address.objects.filter(id=foreign.id).exists()


def test_the_first_address_becomes_the_default(auth_client):
    response = auth_client.post("/api/addresses/", PAYLOAD, format="json")
    assert Address.objects.get(id=response.data["id"]).is_default is True


def test_marking_an_address_default_clears_the_previous_default(auth_client, user):
    first = Address.objects.create(user=user, is_default=True, **PAYLOAD)
    second = Address.objects.create(user=user, **PAYLOAD)

    response = auth_client.patch(f"/api/addresses/{second.id}/", {"is_default": True}, format="json")
    assert response.status_code == 200

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_default is False
    assert second.is_default is True


def test_the_client_cannot_assign_an_address_to_another_user(auth_client, user, other_user):
    response = auth_client.post("/api/addresses/", dict(PAYLOAD, user=other_user.id), format="json")
    assert response.status_code == 201
    assert Address.objects.get(id=response.data["id"]).user == user
