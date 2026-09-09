import pytest
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db

VERIFY_URL = "/api/auth/password-reset/verify/"
CONFIRM_URL = "/api/auth/password-reset/confirm/"
NEW_PASSWORD = "An0therStrongPass!"


@pytest.fixture
def credentials(user):
    return {
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": default_token_generator.make_token(user),
    }


def test_verify_accepts_a_fresh_link(api_client, credentials):
    response = api_client.post(VERIFY_URL, credentials, format="json")

    assert response.status_code == 200
    assert response.data == {"valid": True}


def test_verify_rejects_a_tampered_token(api_client, credentials):
    response = api_client.post(
        VERIFY_URL, {**credentials, "token": "not-a-real-token"}, format="json"
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "invalid_reset_link"


def test_verify_rejects_an_unknown_uid(api_client, credentials):
    response = api_client.post(
        VERIFY_URL, {**credentials, "uid": urlsafe_base64_encode(b"9999")}, format="json"
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "invalid_reset_link"


def test_verify_rejects_an_undecodable_uid(api_client, credentials):
    response = api_client.post(VERIFY_URL, {**credentials, "uid": "!!!"}, format="json")

    assert response.status_code == 400
    assert response.data["error"]["code"] == "invalid_reset_link"


def test_confirm_sets_the_new_password(api_client, user, credentials):
    response = api_client.post(
        CONFIRM_URL, {**credentials, "new_password": NEW_PASSWORD}, format="json"
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)


def test_the_new_password_works_at_the_login_endpoint(api_client, user, credentials, user_password):
    api_client.post(CONFIRM_URL, {**credentials, "new_password": NEW_PASSWORD}, format="json")

    accepted = api_client.post(
        "/api/auth/login/", {"email": user.email, "password": NEW_PASSWORD}, format="json"
    )
    rejected = api_client.post(
        "/api/auth/login/", {"email": user.email, "password": user_password}, format="json"
    )

    assert accepted.status_code == 200
    assert rejected.status_code == 401


def test_a_token_cannot_be_replayed(api_client, credentials):
    api_client.post(CONFIRM_URL, {**credentials, "new_password": NEW_PASSWORD}, format="json")

    replay = api_client.post(
        CONFIRM_URL, {**credentials, "new_password": "YetAnotherPass9!"}, format="json"
    )

    assert replay.status_code == 400
    assert replay.data["error"]["code"] == "invalid_reset_link"


def test_an_expired_token_is_rejected(api_client, credentials, settings):
    # -1, not 0: Django's check is `(now - issued) > PASSWORD_RESET_TIMEOUT`, and
    # a token minted in this same second gives `0 > 0`, which is False — a zero
    # timeout would leave the token valid and this test would fail.
    settings.PASSWORD_RESET_TIMEOUT = -1

    response = api_client.post(
        CONFIRM_URL, {**credentials, "new_password": NEW_PASSWORD}, format="json"
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "invalid_reset_link"


def test_a_weak_password_is_rejected_with_field_errors(api_client, credentials):
    response = api_client.post(CONFIRM_URL, {**credentials, "new_password": "123"}, format="json")

    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"
    assert "new_password" in response.data["error"]["details"]


def test_confirm_revokes_refresh_tokens_issued_before_the_reset(api_client, user, credentials):
    refresh = str(RefreshToken.for_user(user))

    api_client.post(CONFIRM_URL, {**credentials, "new_password": NEW_PASSWORD}, format="json")

    response = api_client.post("/api/auth/refresh/", {"refresh": refresh}, format="json")
    assert response.status_code == 401
