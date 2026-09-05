from datetime import timedelta

import django_filters
from django.db.models import DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.orders.models import OrderStatus

from .models import Category, Product

BEST_SELLING_WINDOWS = {
    "week": timedelta(days=7),
    "month": timedelta(days=30),
    "year": timedelta(days=365),
}


class ProductFilter(django_filters.FilterSet):
    """Every catalog query parameter. Lookups stay `icontains` so the same code
    runs unchanged on SQLite and PostgreSQL."""

    search = django_filters.CharFilter(method="filter_search")
    category = django_filters.CharFilter(method="filter_category")
    roaster = django_filters.CharFilter(field_name="roaster__slug", lookup_expr="iexact")
    type = django_filters.CharFilter(field_name="product_type", lookup_expr="iexact")
    # Slug lookups rather than ModelChoiceFilter: a validated choice field would
    # 400 on a stale slug, and a browse endpoint should just come back empty.
    # The Swagger dropdown comes from the schema hook in `schema.py`.
    origin = django_filters.CharFilter(
        field_name="coffee_profile__origin__slug", lookup_expr="iexact"
    )
    process = django_filters.CharFilter(field_name="coffee_profile__process", lookup_expr="iexact")
    roast = django_filters.CharFilter(
        field_name="coffee_profile__roast_level", lookup_expr="iexact"
    )

    # "Any active variant within the range" — so min_price tests the product's
    # dearest variant and max_price tests its cheapest.
    min_price = django_filters.NumberFilter(field_name="price_max", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price_min", lookup_expr="lte")
    on_sale = django_filters.BooleanFilter(field_name="has_sale")
    in_stock = django_filters.BooleanFilter(field_name="has_stock")
    best_selling = django_filters.ChoiceFilter(
        choices=[(window, window) for window in BEST_SELLING_WINDOWS],
        method="filter_best_selling",
    )
    # `ordering` is not in Meta.fields — it is a declared filter, not a model
    # field, and django-filter rejects non-model names there.
    ordering = django_filters.OrderingFilter(
        fields=(
            ("price_min", "price"),
            ("created_at", "created_at"),
            ("rating_avg", "rating_avg"),
            ("name", "name"),
        )
    )

    class Meta:
        model = Product
        fields = [
            "search", "category", "roaster", "type", "origin", "process", "roast",
            "min_price", "max_price", "on_sale", "in_stock", "best_selling",
        ]

    def filter_search(self, queryset, name, value):
        term = value.strip()
        if not term:
            return queryset
        # `distinct` because the SKU, category and roaster joins can match a
        # product through more than one row.
        return queryset.filter(
            Q(name__icontains=term)
            | Q(short_description__icontains=term)
            | Q(description__icontains=term)
            | Q(variants__sku__icontains=term)
            | Q(category__name__icontains=term)
            # Also match the parent category, so searching a top-level name like
            # "Roasting Machines" finds products filed under its children.
            | Q(category__parent__name__icontains=term)
            | Q(roaster__name__icontains=term)
            | Q(coffee_profile__origin__name__icontains=term)
        ).distinct()

    def filter_category(self, queryset, name, value):
        try:
            category = Category.objects.get(slug=value)
        except Category.DoesNotExist:
            return queryset.none()
        # Browsing "Coffee" must return everything nested beneath it.
        return queryset.filter(category_id__in=category.descendant_ids())

    def filter_best_selling(self, queryset, name, value):
        cutoff = timezone.now() - BEST_SELLING_WINDOWS[value]
        sold_in_window = Q(
            variants__order_items__order__created_at__gte=cutoff
        ) & ~Q(variants__order_items__order__status=OrderStatus.CANCELLED)
        return queryset.annotate(
            sold_qty=Coalesce(
                Sum("variants__order_items__quantity", filter=sold_in_window),
                0,
                output_field=DecimalField(),
            )
        ).order_by("-sold_qty")
