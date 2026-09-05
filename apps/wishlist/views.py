from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import WishlistItem
from .serializers import WishlistItemSerializer, WishlistItemWriteSerializer


class WishlistView(generics.ListCreateAPIView):
    serializer_class = WishlistItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            WishlistItem.objects.filter(user=self.request.user)
            .select_related("product__category", "product__roaster")
            .prefetch_related("product__variants", "product__images")
        )

    def create(self, request, *args, **kwargs):
        serializer = WishlistItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Idempotent: saving twice is a no-op, not an error the UI must handle.
        item, created = WishlistItem.objects.get_or_create(
            user=request.user, product=serializer.validated_data["product"]
        )
        return Response(
            WishlistItemSerializer(item).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class WishlistItemDeleteView(generics.DestroyAPIView):
    """Keyed on the product id, so the frontend need not track wishlist row ids."""

    permission_classes = [IsAuthenticated]
    lookup_field = "product_id"

    def get_queryset(self):
        return WishlistItem.objects.filter(user=self.request.user)
