from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework.exceptions import NotFound, ValidationError

from apps.core.exceptions import DomainError, OutOfStockError, api_exception_handler


def test_domain_error_carries_code_message_and_status():
    error = OutOfStockError()
    assert error.code == "out_of_stock"
    assert error.status_code == 409
    assert error.message


def test_domain_error_accepts_an_override_message_and_details():
    error = DomainError("Custom failure", details={"field": "value"})
    assert error.message == "Custom failure"
    assert error.details == {"field": "value"}


def test_handler_renders_a_domain_error_in_the_envelope():
    response = api_exception_handler(OutOfStockError(details={"sku": "JORY-1"}), {})
    assert response.status_code == 409
    assert response.data == {
        "error": {
            "code": "out_of_stock",
            "message": OutOfStockError.message,
            "details": {"sku": "JORY-1"},
        }
    }


def test_handler_renders_a_drf_error_in_the_same_envelope():
    response = api_exception_handler(NotFound(), {})
    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"
    assert response.data["error"]["message"]


def test_handler_keeps_per_field_details_for_validation_errors():
    response = api_exception_handler(ValidationError({"email": ["This field is required."]}), {})
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"
    assert response.data["error"]["details"] == {"email": ["This field is required."]}


def test_handler_returns_none_for_unhandled_exceptions():
    assert api_exception_handler(RuntimeError("boom"), {}) is None


def test_handler_codes_a_django_http404_as_not_found():
    # DRF hands the original Http404 to the handler, not the NotFound it renders.
    response = api_exception_handler(Http404(), {})
    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"


def test_handler_codes_a_django_permission_denied():
    response = api_exception_handler(PermissionDenied(), {})
    assert response.status_code == 403
    assert response.data["error"]["code"] == "permission_denied"
