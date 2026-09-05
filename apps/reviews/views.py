from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from apps.catalog.models import Product
from apps.core.exceptions import ReviewNotPermittedError

from .models import Review
from .serializers import ReviewSerializer
from .services import has_received_product


class ProductReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_product(self):
        lookup_value = self.kwargs["product_lookup"]
        lookup = Q(slug=lookup_value)
        if lookup_value.isdigit():
            lookup |= Q(pk=int(lookup_value))
        return get_object_or_404(Product, lookup, is_active=True)

    def get_queryset(self):
        return Review.objects.filter(
            product=self.get_product(), is_approved=True
        ).select_related("user")

    def perform_create(self, serializer):
        product = self.get_product()
        if not has_received_product(self.request.user, product):
            raise ReviewNotPermittedError(details={"product": product.slug})

        # `product` and `user` are not in the payload, so DRF's uniqueness
        # validator cannot see the unique_together — check it here rather than
        # letting the database raise an IntegrityError.
        if Review.objects.filter(product=product, user=self.request.user).exists():
            raise serializers.ValidationError(
                {"detail": "You have already reviewed this product."}
            )

        serializer.save(product=product, user=self.request.user)


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Scoped to the author, so someone else's review is 404, not 403.
        return Review.objects.filter(user=self.request.user)
