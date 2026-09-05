import pytest
from django.contrib.auth import get_user_model

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_register_creates_a_user_and_returns_it(api_client):
    response = api_client.post(
        "/api/auth/register/",
        {
            "email": "new@example.com",
            "full_name": "New Shopper",
            "phone": "+201111111111",
            "password": "StrongPassw0rd!",
            "password_confirm": "StrongPassw0rd!",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["email"] == "new@example.com"
    assert "password" not in response.data
    assert User.objects.filter(email="new@example.com").exists()


def test_register_rejects_mismatched_password_confirmation(api_client):
    response = api_client.post(
        "/api/auth/register/",
        {
            "email": "new@example.com",
            "full_name": "New Shopper",
            "password": "StrongPassw0rd!",
            "password_confirm": "DifferentPassw0rd!",
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"


def test_register_rejects_a_weak_password(api_client):
    response = api_client.post(
        "/api/auth/register/",
        {
            "email": "new@example.com",
            "full_name": "New Shopper",
            "password": "123",
            "password_confirm": "123",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "password" in response.data["error"]["details"]


def test_register_rejects_a_duplicate_email(api_client, user):
    response = api_client.post(
        "/api/auth/register/",
        {
            "email": user.email,
            "full_name": "Impostor",
            "password": "StrongPassw0rd!",
            "password_confirm": "StrongPassw0rd!",
        },
        format="json",
    )
    assert response.status_code == 400


def test_login_returns_tokens_and_the_user(api_client, user, user_password):
    response = api_client.post(
        "/api/auth/login/",
        {"email": user.email, "password": user_password},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["access"]
    assert response.data["refresh"]
    assert response.data["user"]["email"] == user.email


def test_login_rejects_a_bad_password(api_client, user):
    response = api_client.post(
        "/api/auth/login/",
        {"email": user.email, "password": "WrongPassw0rd!"},
        format="json",
    )
    assert response.status_code == 401


def test_refresh_returns_a_new_access_token(api_client, user, user_password):
    login = api_client.post(
        "/api/auth/login/",
        {"email": user.email, "password": user_password},
        format="json",
    )
    response = api_client.post(
        "/api/auth/refresh/", {"refresh": login.data["refresh"]}, format="json"
    )
    assert response.status_code == 200
    assert response.data["access"]


def test_logout_blacklists_the_refresh_token(api_client, auth_client, user, user_password):
    login = api_client.post(
        "/api/auth/login/",
        {"email": user.email, "password": user_password},
        format="json",
    )
    refresh = login.data["refresh"]

    logout = auth_client.post("/api/auth/logout/", {"refresh": refresh}, format="json")
    assert logout.status_code == 205

    reuse = api_client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
    assert reuse.status_code == 401


def test_me_requires_authentication(api_client):
    assert api_client.get("/api/auth/me/").status_code == 401


def test_me_returns_and_updates_the_current_user(auth_client, user):
    response = auth_client.get("/api/auth/me/")
    assert response.status_code == 200
    assert response.data["email"] == user.email

    patched = auth_client.patch("/api/auth/me/", {"full_name": "Renamed"}, format="json")
    assert patched.status_code == 200
    assert patched.data["full_name"] == "Renamed"
    user.refresh_from_db()
    assert user.full_name == "Renamed"


def test_me_cannot_change_the_email_or_staff_flag(auth_client, user):
    response = auth_client.patch(
        "/api/auth/me/", {"email": "hijack@example.com", "is_staff": True}, format="json"
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email != "hijack@example.com"
    assert user.is_staff is False


def test_change_password_replaces_the_password(auth_client, user, user_password):
    response = auth_client.post(
        "/api/auth/change-password/",
        {"current_password": user_password, "new_password": "BrandNewPassw0rd!"},
        format="json",
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password("BrandNewPassw0rd!")


def test_change_password_rejects_a_wrong_current_password(auth_client, user):
    response = auth_client.post(
        "/api/auth/change-password/",
        {"current_password": "NotMyPassw0rd!", "new_password": "BrandNewPassw0rd!"},
        format="json",
    )
    assert response.status_code == 400
