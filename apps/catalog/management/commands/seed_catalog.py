"""Populate a browsable demo catalog. Idempotent — keyed on slug and SKU."""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import (
    Category,
    CoffeeProfile,
    Grind,
    Origin,
    Process,
    Product,
    ProductType,
    ProductVariant,
    RoastLevel,
    Roaster,
)

CATEGORIES = [
    ("Coffee", ["Single Origin", "Blends", "Decaf"]),
    ("Equipment", ["Grinders", "Brewers", "Kettles"]),
    ("Roasting Machines", ["Home Roasters", "Shop Roasters"]),
]

ROASTERS = [
    ("Jory Roastery", "Egypt", "Our own small-batch roastery in Cairo."),
    ("Nile Coffee Co.", "Egypt", "Specialty roasters working with East African farms."),
]

COFFEES = [
    {
        "name": "Ethiopia Yirgacheffe",
        "category": "Single Origin",
        "roaster": "Jory Roastery",
        "short_description": "Floral and bright, with jasmine and citrus.",
        "profile": {
            "origin": "Ethiopia",
            "region": "Yirgacheffe",
            "process": Process.WASHED,
            "variety": "Heirloom",
            "roast_level": RoastLevel.LIGHT,
            "altitude_masl": 1900,
            "tasting_notes": "Jasmine, lemon, black tea",
            "cupping_score": Decimal("87.5"),
        },
        "variants": [
            ("JORY-ETH-250", "250g", 250, Decimal("250.00"), None, 25),
            ("JORY-ETH-1000", "1kg", 1000, Decimal("850.00"), None, 10),
        ],
    },
    {
        "name": "Colombia Huila",
        "category": "Single Origin",
        "roaster": "Nile Coffee Co.",
        "short_description": "Caramel sweetness with a red-apple finish.",
        "profile": {
            "origin": "Colombia",
            "region": "Huila",
            "process": Process.WASHED,
            "variety": "Caturra",
            "roast_level": RoastLevel.MEDIUM,
            "altitude_masl": 1700,
            "tasting_notes": "Caramel, red apple, cocoa",
            "cupping_score": Decimal("85.0"),
        },
        "variants": [
            ("JORY-COL-250", "250g", 250, Decimal("220.00"), Decimal("260.00"), 30),
            ("JORY-COL-1000", "1kg", 1000, Decimal("760.00"), None, 8),
        ],
    },
    {
        "name": "Jory House Blend",
        "category": "Blends",
        "roaster": "Jory Roastery",
        "short_description": "Our everyday espresso: chocolate, hazelnut, brown sugar.",
        "profile": {
            "origin": "Brazil / Ethiopia",
            "process": Process.NATURAL,
            "variety": "Blend",
            "roast_level": RoastLevel.MEDIUM_DARK,
            "tasting_notes": "Dark chocolate, hazelnut, brown sugar",
        },
        "variants": [
            ("JORY-HB-250", "250g", 250, Decimal("190.00"), None, 40),
            ("JORY-HB-1000", "1kg", 1000, Decimal("660.00"), None, 15),
        ],
    },
]

HARDWARE = [
    {
        "name": "Hand Grinder Pro",
        "category": "Grinders",
        "type": ProductType.EQUIPMENT,
        "short_description": "Stainless burrs, 40 clicks of adjustment.",
        "variants": [("JORY-GRIND-HAND", "Default", None, Decimal("1200.00"), None, 12)],
    },
    {
        "name": "Pour Over Kit",
        "category": "Brewers",
        "type": ProductType.EQUIPMENT,
        "short_description": "Dripper, server and 100 filters.",
        "variants": [("JORY-BREW-V60", "Default", None, Decimal("650.00"), Decimal("800.00"), 20)],
    },
    {
        "name": "Gooseneck Kettle 1L",
        "category": "Kettles",
        "type": ProductType.ACCESSORY,
        "short_description": "Precise pour, variable temperature.",
        "variants": [("JORY-KETTLE-1L", "1L", None, Decimal("1450.00"), None, 7)],
    },
    {
        "name": "Home Roaster 300g",
        "category": "Home Roasters",
        "type": ProductType.ROASTING_MACHINE,
        "short_description": "Drum roaster for 300g batches with a profile display.",
        "variants": [("JORY-ROAST-300", "300g batch", None, Decimal("18500.00"), None, 3)],
    },
    {
        "name": "Shop Roaster 5kg",
        "category": "Shop Roasters",
        "type": ProductType.ROASTING_MACHINE,
        "short_description": "Commercial 5kg drum roaster with airflow control.",
        "variants": [("JORY-ROAST-5K", "5kg batch", None, Decimal("240000.00"), None, 1)],
    },
]


class Command(BaseCommand):
    help = "Create a demo catalog of coffee, roasteries, equipment and roasting machines."

    @transaction.atomic
    def handle(self, *args, **options):
        categories = self._seed_categories()
        roasters = self._seed_roasters()
        self._seed_coffees(categories, roasters)
        self._seed_hardware(categories)
        self.stdout.write(self.style.SUCCESS(
            f"Catalog ready: {Category.objects.count()} categories, "
            f"{Product.objects.count()} products, {ProductVariant.objects.count()} variants."
        ))

    def _seed_categories(self):
        categories = {}
        for order, (parent_name, child_names) in enumerate(CATEGORIES):
            parent, _ = Category.objects.get_or_create(
                name=parent_name, parent=None, defaults={"display_order": order}
            )
            categories[parent_name] = parent
            for child_order, child_name in enumerate(child_names):
                child, _ = Category.objects.get_or_create(
                    name=child_name, parent=parent, defaults={"display_order": child_order}
                )
                categories[child_name] = child
        return categories

    def _seed_roasters(self):
        roasters = {}
        for name, country, bio in ROASTERS:
            roaster, _ = Roaster.objects.get_or_create(
                name=name, defaults={"country": country, "bio": bio}
            )
            roasters[name] = roaster
        return roasters

    def _seed_coffees(self, categories, roasters):
        for entry in COFFEES:
            product, _ = Product.objects.get_or_create(
                name=entry["name"],
                defaults={
                    "category": categories[entry["category"]],
                    "roaster": roasters[entry["roaster"]],
                    "product_type": ProductType.COFFEE,
                    "short_description": entry["short_description"],
                    "description": entry["short_description"],
                    "is_featured": True,
                },
            )
            profile = dict(entry["profile"])
            profile["origin"], _ = Origin.objects.get_or_create(name=profile["origin"])
            CoffeeProfile.objects.get_or_create(product=product, defaults=profile)
            self._seed_variants(product, entry["variants"], grind=Grind.WHOLE_BEAN)

    def _seed_hardware(self, categories):
        for entry in HARDWARE:
            product, _ = Product.objects.get_or_create(
                name=entry["name"],
                defaults={
                    "category": categories[entry["category"]],
                    "product_type": entry["type"],
                    "short_description": entry["short_description"],
                    "description": entry["short_description"],
                },
            )
            self._seed_variants(product, entry["variants"])

    def _seed_variants(self, product, variants, grind=""):
        for sku, label, weight, price, compare_at, stock in variants:
            ProductVariant.objects.get_or_create(
                sku=sku,
                defaults={
                    "product": product,
                    "label": label,
                    "weight_grams": weight,
                    "grind": grind,
                    "price": price,
                    "compare_at_price": compare_at,
                    "stock_quantity": stock,
                },
            )
