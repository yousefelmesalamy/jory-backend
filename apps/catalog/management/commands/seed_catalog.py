"""Load the catalog in apps/catalog/seed_data.py.

Idempotent — keyed on slug and SKU, so re-running updates copy in place rather
than duplicating rows. The dataset itself lives next door in `seed_data`; this
file is only the loader.
"""

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.catalog import seed_data
from apps.catalog.models import (
    Brand,
    Category,
    CoffeeProfile,
    Flavor,
    Grind,
    HardwareProfile,
    Origin,
    Product,
    ProductImage,
    ProductType,
    ProductVariant,
    Roaster,
)

# One file on disk, referenced by every coffee. ImageField stores a path, not
# the bytes, so 60 rows pointing at one image cost 60 short strings.
PACK_IMAGE = "products/jory-pack-1kg.png"

# Marked-down products get a compare_at this much above the sale price. Derived
# rather than typed per row so the DB check constraint (compare_at > price)
# cannot be tripped by a typo in the dataset.
SALE_MARKUP = Decimal("1.20")


def _round_to_5(amount):
    """Prices land on a multiple of 5 EGP — 3.55 x 265 is not a shelf price."""
    return (amount / 5).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 5


def _weight_label(grams):
    return f"{grams // 1000}kg" if grams >= 1000 and grams % 1000 == 0 else f"{grams}g"


class Command(BaseCommand):
    help = "Load the Jory catalog: categories, lookups, coffee, hardware and variants."

    @transaction.atomic
    def handle(self, *args, **options):
        categories = self._seed_categories()
        origins = self._seed_origins()
        flavors = self._seed_flavors()
        roasters = self._seed_roasters()
        brands = self._seed_brands()
        self._seed_coffees(categories, origins, flavors, roasters)
        self._seed_hardware(categories, brands)

        self.stdout.write(self.style.SUCCESS(
            f"Catalog ready: {Category.objects.count()} categories, "
            f"{Product.objects.count()} products, {ProductVariant.objects.count()} variants, "
            f"{ProductImage.objects.count()} images."
        ))
        if not (Path("media") / PACK_IMAGE).exists():
            self.stdout.write(self.style.WARNING(
                f"media/{PACK_IMAGE} is missing — product rows point at it but it will 404."
            ))

    # --- taxonomy and lookups ------------------------------------------------

    def _seed_categories(self):
        categories = {}
        for order, (name, name_ar, product_type, desc, desc_ar, children) in enumerate(
            seed_data.CATEGORIES
        ):
            parent, _ = Category.objects.update_or_create(
                slug=slugify(name),
                defaults={
                    "name": name,
                    "name_ar": name_ar,
                    "parent": None,
                    "description": desc,
                    "description_ar": desc_ar,
                    "display_order": order,
                    # Authoritative here: a root left blank falls back to COFFEE
                    # and would offer roast filters on the machines page.
                    "product_type": product_type,
                },
            )
            categories[name] = parent
            for child_order, (child, child_ar, child_desc, child_desc_ar) in enumerate(children):
                node, _ = Category.objects.update_or_create(
                    slug=slugify(child),
                    defaults={
                        "name": child,
                        "name_ar": child_ar,
                        "parent": parent,
                        "description": child_desc,
                        "description_ar": child_desc_ar,
                        "display_order": child_order,
                    },
                )
                categories[child] = node
        return categories

    def _seed_origins(self):
        return {
            name: Origin.objects.update_or_create(
                slug=slugify(name), defaults={"name": name, "name_ar": name_ar}
            )[0]
            for name, name_ar in seed_data.ORIGINS
        }

    def _seed_flavors(self):
        return {
            name: Flavor.objects.update_or_create(
                slug=slugify(name), defaults={"name": name, "name_ar": name_ar}
            )[0]
            for name, name_ar in seed_data.FLAVORS
        }

    def _seed_roasters(self):
        return {
            name: Roaster.objects.update_or_create(
                slug=slugify(name),
                defaults={"name": name, "country": country, "bio": bio, "bio_ar": bio_ar},
            )[0]
            for name, country, bio, bio_ar in seed_data.ROASTERS
        }

    def _seed_brands(self):
        return {
            name: Brand.objects.update_or_create(
                slug=slugify(name), defaults={"name": name, "name_ar": name_ar, "country": country}
            )[0]
            for name, name_ar, country in seed_data.BRANDS
        }

    # --- products ------------------------------------------------------------

    def _seed_coffees(self, categories, origins, flavors, roasters):
        for entry in seed_data.COFFEES:
            product, _ = Product.objects.update_or_create(
                slug=slugify(entry["name"]),
                defaults={
                    "name": entry["name"],
                    "name_ar": entry["name_ar"],
                    "category": categories[entry["category"]],
                    "roaster": roasters[entry["roaster"]],
                    "product_type": ProductType.COFFEE,
                    "short_description": entry["short_description"],
                    "short_description_ar": entry["short_description_ar"],
                    "description": entry["description"],
                    "description_ar": entry["description_ar"],
                    "is_featured": entry.get("featured", False),
                    "is_active": True,
                },
            )

            profile = dict(entry["profile"])
            profile["origin"] = origins[profile["origin"]]
            if "flavor" in entry:
                profile["flavor"] = flavors[entry["flavor"]]
            CoffeeProfile.objects.update_or_create(product=product, defaults=profile)

            self._seed_pack_image(product)
            self._seed_coffee_variants(product, entry)

    def _seed_pack_image(self, product):
        ProductImage.objects.update_or_create(
            product=product,
            image=PACK_IMAGE,
            defaults={
                "alt_text": f"{product.name} in a 1kg Jory Cafe pack",
                "is_primary": True,
                "display_order": 0,
            },
        )

    def _seed_coffee_variants(self, product, entry):
        """One SKU per weight x grind. `base_price` is the price of the first
        size at any grind — grind is a mill setting, not a cost."""
        base = entry["base_price"]
        sizes = entry.get("sizes", seed_data.SIZES)
        on_sale = entry.get("sale", False)

        for grams, multiplier in sizes:
            price = _round_to_5(base * multiplier)
            compare_at = _round_to_5(price * SALE_MARKUP) if on_sale else None
            for grind in entry["grinds"]:
                label = _weight_label(grams)
                if grind:
                    # Grind(grind).label is the human string off the TextChoices
                    # ("Whole bean"). The Arabic side is not stored: the variant
                    # serializer already emits a localized `grind` next to
                    # `weight_grams`, so the RTL UI composes its own label.
                    label = f"{label} / {Grind(grind).label}"
                ProductVariant.objects.update_or_create(
                    sku=f"JORY-{entry['code']}-{grams}-{seed_data.GRIND_CODES[grind]}",
                    defaults={
                        "product": product,
                        "label": label,
                        "weight_grams": grams,
                        "grind": grind,
                        "price": price,
                        "compare_at_price": compare_at,
                        "stock_quantity": entry["stock"],
                        "is_active": True,
                    },
                )

    def _seed_hardware(self, categories, brands):
        for entry in seed_data.HARDWARE:
            product, _ = Product.objects.update_or_create(
                slug=slugify(entry["name"]),
                defaults={
                    "name": entry["name"],
                    "name_ar": entry["name_ar"],
                    "category": categories[entry["category"]],
                    "roaster": None,
                    "product_type": entry["type"],
                    "short_description": entry["short_description"],
                    "short_description_ar": entry["short_description_ar"],
                    "description": entry["description"],
                    "description_ar": entry["description_ar"],
                    "is_active": True,
                },
            )
            HardwareProfile.objects.update_or_create(
                product=product,
                defaults={
                    "brand": brands[entry["brand"]],
                    "machine_type": entry["machine_type"],
                },
            )
            for suffix, label, _label_ar, price, compare_at, stock in entry["variants"]:
                ProductVariant.objects.update_or_create(
                    sku=f"JORY-{entry['code']}-{suffix}",
                    defaults={
                        "product": product,
                        "label": label,
                        "weight_grams": None,
                        "grind": "",
                        "price": price,
                        "compare_at_price": compare_at,
                        "stock_quantity": stock,
                        "is_active": True,
                    },
                )
