from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, username=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        if not username:
            raise ValueError("A username is required.")
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        user = self.model(email=self.normalize_email(email), username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, username=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("A superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("A superuser must have is_superuser=True.")
        return self.create_user(email, password, username, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Shoppers and staff. Email is the login identifier; username is a
    required, unique handle a shopper can also log in with."""

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "full_name"]

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email


class Address(TimeStampedModel):
    """A reusable shipping target. Checkout snapshots these values onto the order."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=32)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    area = models.CharField(max_length=100, blank=True)
    street_address = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "-created_at"]
        verbose_name_plural = "addresses"

    def __str__(self):
        return f"{self.full_name}, {self.city}"
