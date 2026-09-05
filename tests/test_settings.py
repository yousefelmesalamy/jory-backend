from decimal import Decimal

from django.conf import settings


def test_secret_key_is_not_the_generated_insecure_default():
    assert not settings.SECRET_KEY.startswith("django-insecure-")
    assert len(settings.SECRET_KEY) >= 40


def test_storefront_money_settings_are_decimals():
    assert isinstance(settings.SHIPPING_FLAT_RATE, Decimal)
    assert isinstance(settings.FREE_SHIPPING_THRESHOLD, Decimal)
    assert settings.DEFAULT_CURRENCY


def test_rest_framework_uses_jwt_and_the_custom_exception_handler():
    assert settings.REST_FRAMEWORK["EXCEPTION_HANDLER"] == "apps.core.exceptions.api_exception_handler"
    assert (
        "rest_framework_simplejwt.authentication.JWTAuthentication"
        in settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]
    )
