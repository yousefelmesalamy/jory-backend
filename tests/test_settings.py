from decimal import Decimal

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from Jory.settings import validate_frontend_url


def test_secret_key_is_not_the_generated_insecure_default():
    assert not settings.SECRET_KEY.startswith("django-insecure-")
    assert len(settings.SECRET_KEY) >= 40


def test_storefront_money_settings_are_decimals():
    assert isinstance(settings.SHIPPING_FLAT_RATE, Decimal)
    assert isinstance(settings.FREE_SHIPPING_THRESHOLD, Decimal)
    assert settings.DEFAULT_CURRENCY


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:4200",
        "http://localhost:4200/",
        "http://127.0.0.1:4200",
        "http://[::1]:4200",
    ],
)
def test_local_frontend_url_is_refused_in_production(url):
    # The whole failure this guards against: FRONTEND_URL left unset on the
    # deployed API, so reset emails go out pointing at the shopper's own machine.
    with pytest.raises(ImproperlyConfigured):
        validate_frontend_url(url, debug=False)


@pytest.mark.parametrize("url", ["http://localhost:4200", "http://127.0.0.1:4200"])
def test_local_frontend_url_is_the_point_in_development(url):
    assert validate_frontend_url(url, debug=True) == url


def test_deployed_frontend_url_passes_in_production():
    url = "https://jory-rust.vercel.app"
    assert validate_frontend_url(url, debug=False) == url


def test_rest_framework_uses_jwt_and_the_custom_exception_handler():
    assert settings.REST_FRAMEWORK["EXCEPTION_HANDLER"] == "apps.core.exceptions.api_exception_handler"
    assert (
        "rest_framework_simplejwt.authentication.JWTAuthentication"
        in settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]
    )
