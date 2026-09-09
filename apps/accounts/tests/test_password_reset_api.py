from unittest import mock

import pytest
from django.core import mail
from django.core.cache import cache
from rest_framework.throttling import SimpleRateThrottle

pytestmark = pytest.mark.django_db

URL = "/api/auth/password-reset/"


def throttled_at(rate):
    """Force the password-reset rate for one test.

    The rate is None whenever DEBUG is on, and the suite runs against the local
    .env — so the throttle test has to switch it back on for itself. Patching
    the dict rather than the setting is deliberate: DRF copies
    DEFAULT_THROTTLE_RATES onto SimpleRateThrottle at import time, so
    override_settings(REST_FRAMEWORK=...) never reaches the throttle.
    """
    return mock.patch.dict(SimpleRateThrottle.THROTTLE_RATES, {"password_reset": rate})


@pytest.fixture(autouse=True)
def clear_throttle_state():
    # DRF keeps throttle history in the cache, which outlives a single test.
    # Without this the sixth test to call the endpoint 429s for no visible reason.
    cache.clear()
    yield
    cache.clear()


def test_a_known_address_gets_one_mail_with_a_link(api_client, user):
    response = api_client.post(URL, {"email": user.email}, format="json")

    assert response.status_code == 200
    assert len(mail.outbox) == 1
    assert "/account/reset-password?uid=" in mail.outbox[0].body


def test_an_unknown_address_looks_identical_and_sends_nothing(api_client, user):
    known = api_client.post(URL, {"email": user.email}, format="json")
    mail.outbox.clear()

    unknown = api_client.post(URL, {"email": "nobody@example.com"}, format="json")

    assert unknown.status_code == known.status_code
    assert unknown.data == known.data
    assert mail.outbox == []


def test_a_malformed_address_also_looks_identical(api_client, user):
    known = api_client.post(URL, {"email": user.email}, format="json")
    mail.outbox.clear()

    malformed = api_client.post(URL, {"email": "not-an-email"}, format="json")

    assert malformed.status_code == known.status_code
    assert malformed.data == known.data
    assert mail.outbox == []


def test_a_missing_email_field_also_looks_identical(api_client, user):
    known = api_client.post(URL, {"email": user.email}, format="json")

    missing = api_client.post(URL, {}, format="json")

    assert missing.status_code == known.status_code
    assert missing.data == known.data


def test_the_address_match_ignores_case(api_client, user):
    response = api_client.post(URL, {"email": user.email.upper()}, format="json")

    assert response.status_code == 200
    assert len(mail.outbox) == 1


def test_an_inactive_user_is_not_mailed(api_client, user):
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = api_client.post(URL, {"email": user.email}, format="json")

    assert response.status_code == 200
    assert mail.outbox == []


def test_a_provider_failure_still_returns_the_neutral_response(api_client, user, monkeypatch):
    def explode(self, *args, **kwargs):
        raise RuntimeError("Brevo is down")

    monkeypatch.setattr("django.core.mail.EmailMultiAlternatives.send", explode)

    response = api_client.post(URL, {"email": user.email}, format="json")

    assert response.status_code == 200


def test_the_accept_language_header_picks_the_email_language(api_client, user):
    api_client.post(URL, {"email": user.email}, format="json", HTTP_ACCEPT_LANGUAGE="ar")

    assert "كلمة المرور" in mail.outbox[0].body


@throttled_at("5/hour")
def test_the_sixth_request_in_an_hour_is_throttled(api_client, user):
    for _ in range(5):
        assert api_client.post(URL, {"email": user.email}, format="json").status_code == 200

    sixth = api_client.post(URL, {"email": user.email}, format="json")

    assert sixth.status_code == 429


@throttled_at(None)
def test_no_rate_means_no_throttling(api_client, user):
    for _ in range(8):
        assert api_client.post(URL, {"email": user.email}, format="json").status_code == 200
