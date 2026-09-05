from django.db.models import Exists, F, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import ProductFilter
from .models import Category, Product, ProductVariant, Roaster
from .serializers import (
    CategorySerializer,
    CategorySlimSerializer,
    ProductCreateSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductSuggestionSerializer,
    RoasterSerializer,
)

SUGGESTION_LIMIT = 5


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """The browse tree. Listing returns roots with their children nested."""

    serializer_class = CategorySerializer
    lookup_field = "slug"
    pagination_class = None  # A taxonomy is small and the frontend renders it whole.

    def get_queryset(self):
        queryset = Category.objects.filter(is_active=True).prefetch_related("children")
        if self.action == "list":
            return queryset.filter(parent__isnull=True)
        return queryset


class RoasterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Roaster.objects.filter(is_active=True)
    serializer_class = RoasterSerializer
    lookup_field = "slug"


@extend_schema_view(
    create=extend_schema(
        summary="Create a product",
        description=(
            "Adds a catalog entry. Staff only — send a JWT for a user with "
            "`is_staff`. The slug may be omitted, in which case it is derived "
            "from the name. Variants, images and the coffee profile are attached "
            "afterwards through the admin, so a product created here has no "
            "sellable units and no price until a variant exists."
        ),
        responses={201: ProductCreateSerializer},
    )
)
class ProductViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Public catalog browse, search and filtering; staff-only creation."""

    lookup_field = "slug"
    lookup_value_regex = "[^/]+"  # accepts either a numeric id or a slug
    filterset_class = ProductFilter

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get_object(self):
        # GET /api/products/{slug-or-id}/ — the id path lets the frontend
        # deep-link a cart line or order item that only stored the numeric id.
        queryset = self.filter_queryset(self.get_queryset())
        lookup_value = self.kwargs[self.lookup_url_kwarg or self.lookup_field]
        lookup = Q(slug=lookup_value)
        if lookup_value.isdigit():
            lookup |= Q(pk=int(lookup_value))
        obj = get_object_or_404(queryset, lookup)
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        active_variants = ProductVariant.objects.filter(product=OuterRef("pk"), is_active=True)
        return (
            Product.objects.filter(is_active=True)
            .select_related("category", "roaster", "coffee_profile")
            .prefetch_related("variants", "images")
            # Correlated subqueries, not Min()/Max() over the join: a search that
            # filters on variants must not change the price we report.
            .annotate(
                price_min=Subquery(active_variants.order_by("price").values("price")[:1]),
                price_max=Subquery(active_variants.order_by("-price").values("price")[:1]),
                has_sale=Exists(active_variants.filter(compare_at_price__gt=F("price"))),
                has_stock=Exists(active_variants.filter(stock_quantity__gt=0)),
            )
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ProductCreateSerializer
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer


class SearchSuggestView(APIView):
    """Type-ahead for the search bar: a few products and categories, nothing more."""

    def get(self, request):
        term = request.query_params.get("q", "").strip()
        if not term:
            return Response({"products": [], "categories": []})

        products = (
            Product.objects.filter(is_active=True)
            .filter(
                Q(name__icontains=term)
                | Q(short_description__icontains=term)
                | Q(category__name__icontains=term)
                | Q(roaster__name__icontains=term)
            )
            .prefetch_related("variants")
            .distinct()[:SUGGESTION_LIMIT]
        )
        categories = Category.objects.filter(is_active=True, name__icontains=term)[
            :SUGGESTION_LIMIT
        ]

        context = {"request": request}
        return Response(
            {
                "products": ProductSuggestionSerializer(products, many=True, context=context).data,
                "categories": CategorySlimSerializer(categories, many=True, context=context).data,
            }
        )
