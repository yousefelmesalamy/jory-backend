"""Delete every row the store owns, keeping the people who use it.

Users and their addresses survive: an account is not store data, and dropping
the superusers would lock staff out of the admin that manages everything this
command just emptied. Everything else goes — catalog, carts, orders, vouchers,
reviews and wishlists.

Deletion order is explicit rather than left to cascades. Most of these FKs do
cascade, but OrderItem.variant is SET_NULL and CoffeeProfile.origin is PROTECT,
so relying on cascade order would leave orphaned order lines behind and then
refuse to drop the Origin rows they point at.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.cart.models import Cart, CartItem
from apps.catalog.models import (
    Brand,
    Category,
    CoffeeProfile,
    Flavor,
    HardwareProfile,
    Origin,
    Product,
    ProductImage,
    ProductVariant,
    Roaster,
)
from apps.orders.models import Order, OrderItem
from apps.reviews.models import Review
from apps.vouchers.models import Voucher, VoucherRedemption
from apps.wishlist.models import WishlistItem

# Children before parents, dependants before the rows they point at.
DELETION_ORDER = [
    VoucherRedemption,
    Voucher,
    OrderItem,
    Order,
    CartItem,
    Cart,
    WishlistItem,
    Review,
    ProductImage,
    ProductVariant,
    CoffeeProfile,
    HardwareProfile,
    Product,
    Category,
    Roaster,
    Brand,
    Origin,
    Flavor,
]


class Command(BaseCommand):
    help = (
        "Delete all catalog, cart, order, voucher, review and wishlist rows. "
        "User accounts and their addresses are kept."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Confirm the deletion. Without it the command only reports what it would remove.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        counts = [(model, model.objects.count()) for model in DELETION_ORDER]
        total = sum(count for _, count in counts)

        if not options["yes"]:
            for model, count in counts:
                if count:
                    self.stdout.write(f"  would delete {count:>5}  {model.__name__}")
            raise CommandError(
                f"{total} rows would be deleted. Re-run with --yes to actually delete them."
            )

        for model, count in counts:
            # Queryset.delete() would still emit cascade queries per model; the
            # explicit order above is what guarantees a clean sweep.
            model.objects.all().delete()
            if count:
                self.stdout.write(f"  deleted {count:>5}  {model.__name__}")

        self.stdout.write(self.style.SUCCESS(f"Store emptied: {total} rows deleted, users kept."))
