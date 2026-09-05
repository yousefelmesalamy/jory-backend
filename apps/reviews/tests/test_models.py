import pytest
from django.db import IntegrityError, transaction

from apps.reviews.models import Review

pytestmark = pytest.mark.django_db


def test_a_review_records_its_rating_and_text(user, product):
    review = Review.objects.create(
        product=product, user=user, rating=5, title="Superb", body="Bright and clean."
    )
    assert review.is_approved is True
    assert str(review) == f"5/5 {product.name} by {user.email}"


def test_one_review_per_user_per_product(user, product):
    Review.objects.create(product=product, user=user, rating=4)
    with pytest.raises(IntegrityError):
        Review.objects.create(product=product, user=user, rating=2)


def test_two_users_can_review_the_same_product(user, other_user, product):
    Review.objects.create(product=product, user=user, rating=4)
    Review.objects.create(product=product, user=other_user, rating=5)
    assert product.reviews.count() == 2


@pytest.mark.parametrize("rating", [0, 6])
def test_a_rating_outside_one_to_five_is_rejected_by_the_database(user, product, rating):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Review.objects.create(product=product, user=user, rating=rating)


@pytest.mark.parametrize("rating", [1, 3, 5])
def test_ratings_one_to_five_are_accepted(user, product, rating):
    assert Review.objects.create(product=product, user=user, rating=rating).rating == rating
