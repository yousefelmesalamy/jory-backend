"""Which filters a category exposes, and what each one offers.

A shopper browsing roasting machines is asked about brands, not roast levels —
so the facet list is a function of the category's product type rather than one
fixed rail. Labels are resolved here rather than in the frontend so the copy
deck lives in one place.
"""

from .filters import BEST_SELLING_WINDOWS
from .models import (
    MACHINE_TYPE_LABELS_AR,
    PROCESS_LABELS_AR,
    PRODUCT_TYPE_LABELS_AR,
    ROAST_LEVEL_LABELS_AR,
    Brand,
    Flavor,
    MachineType,
    Origin,
    Process,
    ProductType,
    RoastLevel,
    Roaster,
)

CHOICE = "choice"
RANGE = "range"
BOOLEAN = "boolean"

# Listed in the order the rail draws them.
_HARDWARE = (
    "type", "brand", "machine_type",
    "price", "best_selling", "on_sale", "in_stock", "ordering",
)

FACETS_BY_TYPE = {
    ProductType.COFFEE: (
        "type", "roast", "process", "origin", "flavor", "roaster",
        "price", "best_selling", "on_sale", "in_stock", "ordering",
    ),
    ProductType.EQUIPMENT: _HARDWARE,
    ProductType.ROASTING_MACHINE: _HARDWARE,
    ProductType.ACCESSORY: _HARDWARE,
}

# Browsing everything: no type is known, so only the universal filters apply.
DEFAULT_FACETS = ("type", "price", "best_selling", "on_sale", "in_stock", "ordering")

FACET_KINDS = {
    "type": CHOICE,
    "roast": CHOICE,
    "process": CHOICE,
    "origin": CHOICE,
    "flavor": CHOICE,
    "roaster": CHOICE,
    "brand": CHOICE,
    "machine_type": CHOICE,
    "best_selling": CHOICE,
    "ordering": CHOICE,
    "price": RANGE,
    "on_sale": BOOLEAN,
    "in_stock": BOOLEAN,
}

FACET_LABELS = {
    "type": "Product type",
    "roast": "Roast",
    "process": "Process",
    "origin": "Origin",
    "flavor": "Flavor",
    "roaster": "Roaster",
    "brand": "Brand",
    "machine_type": "Machine type",
    "best_selling": "Best selling",
    "ordering": "Sort by",
    "price": "Price range",
    "on_sale": "On sale",
    "in_stock": "In stock only",
}

FACET_LABELS_AR = {
    "type": "نوع المنتج",
    "roast": "درجة التحميص",
    "process": "المعالجة",
    "origin": "المنشأ",
    "flavor": "النكهة",
    "roaster": "المحمصة",
    "brand": "العلامة التجارية",
    "machine_type": "نوع الآلة",
    "best_selling": "الأكثر مبيعًا",
    "ordering": "الترتيب",
    "price": "نطاق السعر",
    "on_sale": "خصم",
    "in_stock": "المتوفر فقط",
}

BEST_SELLING_LABELS_AR = {
    "week": "هذا الأسبوع",
    "month": "هذا الشهر",
    "year": "هذا العام",
}

# Mirrors ProductFilter.ordering's field map.
ORDERING_OPTIONS = (
    ("-created_at", "Newest", "الأحدث"),
    ("created_at", "Oldest", "الأقدم"),
    ("price", "Price: low to high", "السعر: من الأقل"),
    ("-price", "Price: high to low", "السعر: من الأعلى"),
    ("-rating_avg", "Highest rated", "الأعلى تقييمًا"),
    ("name", "Name: A–Z", "الاسم: أ–ي"),
    ("-name", "Name: Z–A", "الاسم: ي–أ"),
)


def _enum_options(choices, labels_ar, locale):
    """TextChoices -> options. `labels_ar` is keyed by the choice member, which
    hashes as its own value, so a plain string key resolves too."""
    return [
        {"value": value, "label": labels_ar.get(value, label) if locale == "ar" else label}
        for value, label in choices
    ]


def _rows_to_options(rows, locale):
    """Lookup rows -> options. `name_ar` is optional: Roaster has no Arabic
    column and falls back to its English name."""
    return [
        {
            "value": row.slug,
            "label": (getattr(row, "name_ar", "") or row.name) if locale == "ar" else row.name,
        }
        for row in rows
    ]


def _scoped(model, path, category_ids, locale):
    """Lookup rows that at least one active in-scope product actually uses, so
    the rail never offers a pill that returns nothing. `path` is the query
    prefix reaching from the lookup model down to Product."""
    lookups = {"is_active": True, f"{path}__is_active": True}
    if category_ids is not None:
        lookups[f"{path}__category_id__in"] = category_ids
    return _rows_to_options(model.objects.filter(**lookups).distinct(), locale)


def _options_for(key, category_ids, locale):
    if key == "type":
        return _enum_options(ProductType.choices, PRODUCT_TYPE_LABELS_AR, locale)
    if key == "roast":
        return _enum_options(RoastLevel.choices, ROAST_LEVEL_LABELS_AR, locale)
    if key == "process":
        return _enum_options(Process.choices, PROCESS_LABELS_AR, locale)
    if key == "machine_type":
        return _enum_options(MachineType.choices, MACHINE_TYPE_LABELS_AR, locale)
    if key == "best_selling":
        return [
            {
                "value": window,
                "label": BEST_SELLING_LABELS_AR[window] if locale == "ar" else window.title(),
            }
            for window in BEST_SELLING_WINDOWS
        ]
    if key == "ordering":
        return [
            {"value": value, "label": label_ar if locale == "ar" else label_en}
            for value, label_en, label_ar in ORDERING_OPTIONS
        ]
    if key == "origin":
        return _scoped(Origin, "coffee_profiles__product", category_ids, locale)
    if key == "flavor":
        return _scoped(Flavor, "coffee_profiles__product", category_ids, locale)
    if key == "roaster":
        return _scoped(Roaster, "products", category_ids, locale)
    if key == "brand":
        return _scoped(Brand, "hardware_profiles__product", category_ids, locale)
    # price, on_sale and in_stock are not choices — the rail draws their own control.
    return []


def build_facets(category, locale):
    """The ordered facet list for a category, or the universal set when browsing
    everything. `category` may be None."""
    if category is None:
        keys = DEFAULT_FACETS
        category_ids = None
    else:
        keys = FACETS_BY_TYPE[category.effective_product_type]
        category_ids = category.descendant_ids()

    labels = FACET_LABELS_AR if locale == "ar" else FACET_LABELS
    return [
        {
            "key": key,
            "label": labels[key],
            "kind": FACET_KINDS[key],
            "options": _options_for(key, category_ids, locale),
        }
        for key in keys
    ]
