"""Swagger dropdowns for the catalog options that come from the database.

Neither django-filter nor drf-spectacular can emit an OpenAPI enum for choices
that are unknown at import time, which these are — staff add categories and
origins through the admin. Filling them in here keeps the documented options
current without a validated choice field on the *filters*, which would reject a
stale slug with a 400 rather than returning an empty page.

Two dropdowns, deliberately keyed differently:

* the GET /api/products/ filters take **slugs**, matching every other browse URL;
* the POST /api/products/ body takes a category **name**, so the person filling
  the form in Swagger picks the label they know from the admin.
"""

from .models import Category, Flavor, Origin

PRODUCT_LIST_PATH = "/api/products/"
PRODUCT_CREATE_SCHEMA = "ProductCreate"


def _enum(schema, values):
    schema.update(enum=values)


def _add_filter_choices(result):
    operation = result.get("paths", {}).get(PRODUCT_LIST_PATH, {}).get("get")
    if not operation:
        return

    options = {
        "category": list(
            Category.objects.filter(is_active=True).values_list("slug", flat=True)
        ),
        "origin": list(Origin.objects.filter(is_active=True).values_list("slug", flat=True)),
        "flavor": list(Flavor.objects.filter(is_active=True).values_list("slug", flat=True)),
    }
    for parameter in operation.get("parameters", []):
        if parameter["name"] in options:
            parameter["schema"] = {**parameter["schema"], **{"enum": options[parameter["name"]]}}


def _add_create_category_choices(result):
    schema = result.get("components", {}).get("schemas", {}).get(PRODUCT_CREATE_SCHEMA)
    if not schema:
        return

    category = schema.get("properties", {}).get("category")
    if category is None:
        return

    # dict.fromkeys, not set(): duplicate names would repeat in the dropdown, and
    # the admin's display order is a more useful sequence than an arbitrary one.
    names = list(
        dict.fromkeys(Category.objects.filter(is_active=True).values_list("name", flat=True))
    )
    _enum(category, names)
    category["description"] = "Name of an active category, as shown in the admin."


def add_catalog_filter_choices(result, generator, request, public):
    _add_filter_choices(result)
    _add_create_category_choices(result)
    return result
