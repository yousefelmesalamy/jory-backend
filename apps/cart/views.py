from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.vouchers.services import validate_voucher

from .models import Cart, CartItem
from .serializers import (
    CartItemQuantitySerializer,
    CartItemSerializer,
    CartItemWriteSerializer,
    CartSerializer,
    MergeCartSerializer,
    VoucherCodeSerializer,
)
from .services import add_item, calculate_totals, merge_carts, resolve_cart, set_quantity

CART_TOKEN_HEADER = "X-Cart-Token"

NOT_FOUND_BODY = {
    "error": {"code": "not_found", "message": "No such cart item.", "details": {}}
}


class CartContextMixin:
    """Resolves the caller's cart and renders it with server-computed totals."""

    permission_classes = [AllowAny]

    def get_cart(self, request):
        user = request.user if request.user.is_authenticated else None
        cart, _ = resolve_cart(user=user, session_token=request.headers.get(CART_TOKEN_HEADER))
        return cart

    def with_token(self, response, cart):
        if cart.session_token:
            response[CART_TOKEN_HEADER] = str(cart.session_token)
        return response

    def cart_response(self, cart, status_code=status.HTTP_200_OK):
        cart = Cart.objects.prefetch_related("items__variant__product").get(pk=cart.pk)
        serializer = CartSerializer(cart, context={"totals": calculate_totals(cart)})
        return self.with_token(Response(serializer.data, status=status_code), cart)


class CartView(CartContextMixin, APIView):
    def get(self, request):
        return self.cart_response(self.get_cart(request))


class CartItemsView(CartContextMixin, APIView):
    def post(self, request):
        serializer = CartItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = self.get_cart(request)
        item = add_item(
            cart, serializer.validated_data["variant"], serializer.validated_data["quantity"]
        )
        return self.with_token(
            Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED), cart
        )


class CartItemDetailView(CartContextMixin, APIView):
    def get_item(self, request, pk):
        cart = self.get_cart(request)
        # Scoped to the caller's cart, so another shopper's line is 404, not 403.
        return CartItem.objects.filter(cart=cart, pk=pk).first()

    def patch(self, request, pk):
        item = self.get_item(request, pk)
        if item is None:
            return Response(NOT_FOUND_BODY, status=status.HTTP_404_NOT_FOUND)

        serializer = CartItemQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = set_quantity(item, serializer.validated_data["quantity"])
        if updated is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(CartItemSerializer(updated).data)

    def delete(self, request, pk):
        item = self.get_item(request, pk)
        if item is None:
            return Response(NOT_FOUND_BODY, status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplyVoucherView(CartContextMixin, APIView):
    def post(self, request):
        serializer = VoucherCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = self.get_cart(request)
        totals = calculate_totals(cart)
        # Raises VoucherError, which the core exception handler renders.
        cart.voucher = validate_voucher(
            serializer.validated_data["code"], cart.user, totals["subtotal"]
        )
        cart.save(update_fields=["voucher", "updated_at"])
        return self.cart_response(cart)


class RemoveVoucherView(CartContextMixin, APIView):
    def delete(self, request):
        cart = self.get_cart(request)
        cart.voucher = None
        cart.save(update_fields=["voucher", "updated_at"])
        return self.cart_response(cart)


class MergeCartView(CartContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MergeCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_cart, _ = resolve_cart(user=request.user, session_token=None)
        guest_cart = Cart.objects.filter(
            session_token=serializer.validated_data["cart_token"], user__isnull=True
        ).first()
        if guest_cart is not None:
            user_cart = merge_carts(guest_cart, user_cart)
        return self.cart_response(user_cart)
