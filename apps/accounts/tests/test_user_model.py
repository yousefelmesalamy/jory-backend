import pytest
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

User = get_user_model()


def test_the_project_uses_the_custom_user_model(settings):
    assert settings.AUTH_USER_MODEL == "accounts.User"


@pytest.mark.django_db
def test_create_user_normalizes_email_and_hashes_the_password():
    user = User.objects.create_user(
        email="Shopper@Example.COM", password="StrongPassw0rd!", username="shopper1"
    )
    assert user.email == "Shopper@example.com"
    assert user.password != "StrongPassw0rd!"
    assert user.check_password("StrongPassw0rd!")
    assert user.is_active is True
    assert user.is_staff is False


@pytest.mark.django_db
def test_create_user_requires_an_email():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="StrongPassw0rd!", username="shopper1")


@pytest.mark.django_db
def test_create_user_requires_a_username():
    with pytest.raises(ValueError):
        User.objects.create_user(email="shopper@example.com", password="StrongPassw0rd!")


@pytest.mark.django_db
def test_email_is_unique():
    User.objects.create_user(email="dup@example.com", password="StrongPassw0rd!", username="dup1")
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="dup@example.com", password="StrongPassw0rd!", username="dup2")


@pytest.mark.django_db
def test_username_is_unique():
    User.objects.create_user(email="a@example.com", password="StrongPassw0rd!", username="dupname")
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="b@example.com", password="StrongPassw0rd!", username="dupname")


@pytest.mark.django_db
def test_create_superuser_is_staff_and_superuser():
    admin = User.objects.create_superuser(
        email="admin@example.com", password="StrongPassw0rd!", username="admin"
    )
    assert admin.is_staff is True
    assert admin.is_superuser is True


@pytest.mark.django_db
def test_user_string_representation_is_the_email():
    user = User.objects.create_user(
        email="shopper@example.com", password="StrongPassw0rd!", username="shopper2"
    )
    assert str(user) == "shopper@example.com"
