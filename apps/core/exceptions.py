from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class DomainError(Exception):
    """Base for business-rule failures raised by service functions.

    Services raise these; the handler below turns them into HTTP responses, so
    no view contains error-formatting code.
    """

    code = "domain_error"
    message = "The request could not be completed."
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message=None, details=None):
        self.message = message or self.__class__.message
        self.details = details or {}
        super().__init__(self.message)


class VoucherError(DomainError):
    code = "voucher_invalid"
    message = "This voucher cannot be applied."
    status_code = status.HTTP_400_BAD_REQUEST


class VoucherNotFoundError(VoucherError):
    code = "voucher_not_found"
    message = "No voucher matches that code."


class VoucherInactiveError(VoucherError):
    code = "voucher_inactive"
    message = "This voucher is no longer active."


class VoucherNotStartedError(VoucherError):
    code = "voucher_not_started"
    message = "This voucher is not available yet."


class VoucherExpiredError(VoucherError):
    code = "voucher_expired"
    message = "This voucher has expired."


class VoucherMinOrderError(VoucherError):
    code = "voucher_min_order"
    message = "Your subtotal is below this voucher's minimum."


class VoucherExhaustedError(VoucherError):
    code = "voucher_exhausted"
    message = "This voucher has been fully redeemed."


class VoucherUserLimitError(VoucherError):
    code = "voucher_user_limit"
    message = "You have already used this voucher."


class OutOfStockError(DomainError):
    code = "out_of_stock"
    message = "Not enough stock is available for one or more items."
    status_code = status.HTTP_409_CONFLICT


class EmptyCartError(DomainError):
    code = "empty_cart"
    message = "Your cart is empty."
    status_code = status.HTTP_400_BAD_REQUEST


class CartItemUnavailableError(DomainError):
    code = "item_unavailable"
    message = "This item is no longer available."
    status_code = status.HTTP_400_BAD_REQUEST


class OrderNotCancellableError(DomainError):
    code = "order_not_cancellable"
    message = "This order can no longer be cancelled."
    status_code = status.HTTP_409_CONFLICT


class ReviewNotPermittedError(DomainError):
    code = "review_not_permitted"
    message = "You can only review products from an order that was delivered to you."
    status_code = status.HTTP_403_FORBIDDEN


def api_exception_handler(exc, context):
    """Render every API error as {"error": {"code", "message", "details"}}."""
    if isinstance(exc, DomainError):
        return Response(
            {"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
            status=exc.status_code,
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    # DRF translates Django's own Http404/PermissionDenied into API responses but
    # hands us the *original* exception, which carries no `default_code`. Map those
    # two explicitly so a missing object reports "not_found" rather than "error".
    if isinstance(exc, Http404):
        default_code = "not_found"
    elif isinstance(exc, PermissionDenied):
        default_code = "permission_denied"
    else:
        default_code = getattr(exc, "default_code", "error")
    if isinstance(response.data, dict) and not isinstance(response.data.get("detail"), str):
        # Field-level validation errors: keep the per-field mapping in details.
        response.data = {
            "error": {
                "code": "validation_error",
                "message": "The submitted data is invalid.",
                "details": response.data,
            }
        }
    else:
        detail = response.data.get("detail") if isinstance(response.data, dict) else None
        response.data = {
            "error": {
                "code": default_code,
                "message": str(detail) if detail else "The request could not be completed.",
                "details": {},
            }
        }
    return response
