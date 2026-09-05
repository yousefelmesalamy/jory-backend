from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.cart.services import resolve_cart

from .models import Order
from .serializers import CheckoutSerializer, OrderSerializer
from .services import cancel_order, place_order


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Checkout and order history. Orders are never edited or deleted over REST."""

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "order_number"

    def get_queryset(self):
        # Scoped to the caller, so another shopper's order is 404, not 403.
        return Order.objects.filter(user=self.request.user).prefetch_related("items")

    def create(self, request, *args, **kwargs):
        serializer = CheckoutSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        cart, _ = resolve_cart(user=request.user, session_token=None)
        # Raises EmptyCartError / OutOfStockError / VoucherError, which the core
        # handler renders in the standard envelope.
        order = place_order(request.user, cart, serializer.address_data)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, order_number=None):
        return Response(OrderSerializer(cancel_order(self.get_object())).data)
