import uuid
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.cart.models import Cart, CartItem

pytestmark = pytest.mark.django_db


def test_a_user_cart_needs_no_session_token(user):
    cart = Cart.objects.create(user=user)
    assert cart.session_token is None
    assert str(cart) == f"Cart for {user.email}"


def test_a_guest_cart_needs_no_user():
    token = uuid.uuid4()
    cart = Cart.objects.create(session_token=token)
    assert cart.user is None
    assert str(cart) == f"Guest cart {token}"


def test_a_cart_cannot_belong_to_both_a_user_and_a_session(user):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Cart.objects.create(user=user, session_token=uuid.uuid4())


def test_a_cart_cannot_be_orphaned():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Cart.objects.create()


def test_a_user_has_at_most_one_cart(user):
    Cart.objects.create(user=user)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Cart.objects.create(user=user)


def test_session_tokens_are_unique():
    token = uuid.uuid4()
    Cart.objects.create(session_token=token)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Cart.objects.create(session_token=token)


def test_a_line_total_is_price_times_quantity(user, variant):
    cart = Cart.objects.create(user=user)
    item = CartItem.objects.create(cart=cart, variant=variant, quantity=3)
    assert item.line_total == Decimal("750.00")


def test_the_same_variant_cannot_be_added_twice(user, variant):
    cart = Cart.objects.create(user=user)
    CartItem.objects.create(cart=cart, variant=variant, quantity=1)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CartItem.objects.create(cart=cart, variant=variant, quantity=1)


def test_a_zero_quantity_line_is_rejected(user, variant):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            cart = Cart.objects.create(user=user)
            CartItem.objects.create(cart=cart, variant=variant, quantity=0)
