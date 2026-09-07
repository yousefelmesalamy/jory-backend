"""Django settings for the Jory project. All environment-specific values come from .env."""

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import environ
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    JWT_ACCESS_MINUTES=(int, 60),
    JWT_REFRESH_DAYS=(int, 7),
    SECURE_SSL_REDIRECT=(bool, False),
    SECURE_HSTS_SECONDS=(int, 0),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

DJANGO_APPS = [
    # jazzmin must precede django.contrib.admin so its admin template overrides win.
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.catalog",
    "apps.vouchers",
    "apps.cart",
    "apps.orders",
    "apps.wishlist",
    "apps.reviews",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "Jory.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "Jory.wsgi.application"
ASGI_APPLICATION = "Jory.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}

# A relative sqlite:/// URL resolves against the current working directory, which
# would put the database somewhere different depending on where manage.py is run
# from. Anchor it to BASE_DIR instead.
if DATABASES["default"]["ENGINE"].endswith("sqlite3"):
    db_name = Path(DATABASES["default"]["NAME"])
    if not db_name.is_absolute():
        DATABASES["default"]["NAME"] = str(BASE_DIR / db_name)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"

LANGUAGE_CODE = env("LANGUAGE_CODE", default="en-us")
TIME_ZONE = env("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))

# DRF's FileField turns `image.url` into an absolute URL with
# `request.build_absolute_uri()`, which trusts the incoming Host header. Behind
# any proxy that rewrites Host, that bakes the *proxy's* domain into every image
# URL and the storefront gets silent 404s. Setting MEDIA_URL to an absolute URL
# side-steps it: `build_absolute_uri` leaves an already-absolute URL alone.
# Keep the trailing slash — Django joins on it.
MEDIA_URL = env("MEDIA_URL", default="media/")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

# X-Cart-Token needs both halves, and they are not symmetric:
# EXPOSE lets the browser *read* it off the response, ALLOW_HEADERS lets the
# browser *send* it on the next request. With only the first, the guest-cart
# interceptor's `X-Cart-Token` request header fails preflight and /api/cart/ is
# the one endpoint that dies with a CORS error while everything else works.
# Invisible in local development, where the dev proxy makes it same-origin.
CORS_EXPOSE_HEADERS = ["X-Cart-Token"]
CORS_ALLOW_HEADERS = [*default_headers, "x-cart-token"]

# The storefront is served from a different origin than the API (Vercel vs. the
# API host), so the admin's own forms are the only CSRF surface — but Django 4
# still wants the origin listed once the site is behind TLS.
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

# --- Production hardening ----------------------------------------------------
# Only applied with DEBUG off, so local development is untouched.

if not DEBUG:
    # TLS is terminated by the host, which forwards the original scheme. Without
    # this Django thinks every request is plain HTTP and, with SECURE_SSL_REDIRECT
    # on, redirects forever.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    # Off by default: hosts that already force HTTPS at the edge make this
    # redundant, and turning it on before TLS works locks you out of the admin.
    SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT")
    SECURE_HSTS_SECONDS = env("SECURE_HSTS_SECONDS")

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.AllowAny",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Jory API",
    "DESCRIPTION": "API for the Jory e-commerce platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "apps.catalog.schema.add_catalog_filter_choices",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("JWT_ACCESS_MINUTES")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_DAYS")),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# Storefront rules — shipping is configuration, not a table (COD is the only method).
SHIPPING_FLAT_RATE = Decimal(env("SHIPPING_FLAT_RATE", default="30.00"))
FREE_SHIPPING_THRESHOLD = Decimal(env("FREE_SHIPPING_THRESHOLD", default="500.00"))
DEFAULT_CURRENCY = env("DEFAULT_CURRENCY", default="EGP")

# --- Admin dashboard (django-jazzmin) ---------------------------------------
# Catalog writes go through the admin, so this is staff's primary tool, not a
# afterthought. Branding lives in static/jory/; no admin.py file is affected.

JAZZMIN_SETTINGS = {
    "site_title": "Jory Admin",
    "site_header": "Jory",
    "site_brand": "Jory",
    "site_logo": "jory/img/logo.svg",
    # The logo is a 2:1 wordmark — AdminLTE's default img-circle would crop it
    # into a disc, so override the classes rather than the image.
    "site_logo_classes": "img-rounded elevation-0",
    "login_logo": "jory/img/logo.svg",
    "login_logo_dark": "jory/img/logo-light.svg",
    "site_icon": "jory/img/logo.svg",
    "welcome_sign": "Sign in to the Jory admin",
    "copyright": "Jory",
    "search_model": ["catalog.Product", "orders.Order"],
    "user_avatar": None,
    "topmenu_links": [
        {"name": "Dashboard", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"model": "catalog.Product"},
        {"model": "orders.Order"},
    ],
    "usermenu_links": [{"model": "accounts.user"}],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    # Ordered by how often staff touch each area, not alphabetically.
    "order_with_respect_to": [
        "catalog",
        "catalog.category",
        "catalog.roaster",
        "catalog.product",
        "catalog.productvariant",
        "orders",
        "cart",
        # Models are alphabetical within an app unless named here, which would
        # otherwise put Redemptions above Vouchers and Addresses above Users.
        "vouchers",
        "vouchers.voucher",
        "vouchers.voucherredemption",
        "accounts",
        "accounts.user",
        "accounts.address",
        "reviews",
        "wishlist",
        "auth",
        "token_blacklist",
    ],
    "icons": {
        "auth": "fas fa-shield-alt",
        "auth.group": "fas fa-users",
        "accounts": "fas fa-address-book",
        "accounts.user": "fas fa-user",
        "accounts.address": "fas fa-map-marker-alt",
        "catalog": "fas fa-store",
        "catalog.category": "fas fa-sitemap",
        "catalog.roaster": "fas fa-industry",
        "catalog.product": "fas fa-mug-hot",
        "catalog.productvariant": "fas fa-boxes",
        "orders": "fas fa-receipt",
        "orders.order": "fas fa-receipt",
        "cart": "fas fa-shopping-cart",
        "cart.cart": "fas fa-shopping-cart",
        "vouchers": "fas fa-tags",
        "vouchers.voucher": "fas fa-tags",
        "vouchers.voucherredemption": "fas fa-ticket-alt",
        "reviews": "fas fa-star",
        "reviews.review": "fas fa-star",
        "wishlist": "fas fa-heart",
        "wishlist.wishlistitem": "fas fa-heart",
        "token_blacklist": "fas fa-key",
        "token_blacklist.outstandingtoken": "fas fa-key",
        "token_blacklist.blacklistedtoken": "fas fa-ban",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": False,
    "custom_css": "jory/css/jazzmin-jory.css",
    "custom_js": None,
    "show_ui_builder": False,
    "changeform_format": "single",
    # Product and Order carry several inlines each; tabs keep them off one
    # very long scroll.
    "changeform_format_overrides": {
        "catalog.product": "horizontal_tabs",
        "orders.order": "horizontal_tabs",
    },
    "language_chooser": False,
}

# The logo is maroon on transparent, so it needs a light ground to read at all.
JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": True,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": False,
    "accent": "accent-primary",
    "navbar": "navbar-white navbar-light",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-light-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
    "actions_sticky_top": True,
}
