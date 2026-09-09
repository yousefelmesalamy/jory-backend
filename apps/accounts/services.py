import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.core.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES

from .models import Address

logger = logging.getLogger(__name__)

User = get_user_model()

# Short enough to live here rather than in a third template file per locale.
RESET_SUBJECTS = {
    "en": "Reset your Jory password",
    "ar": "إعادة تعيين كلمة مرور جوري",
}


def set_default_address(address):
    """Make `address` the user's only default."""
    Address.objects.filter(user=address.user).exclude(pk=address.pk).update(is_default=False)
    if not address.is_default:
        address.is_default = True
        address.save(update_fields=["is_default", "updated_at"])
    return address


def ensure_default_address(address):
    """Give a user their first address as the default automatically."""
    has_other = Address.objects.filter(user=address.user).exclude(pk=address.pk).exists()
    if not has_other:
        return set_default_address(address)
    if address.is_default:
        return set_default_address(address)
    return address


def build_password_reset_link(user):
    """The storefront URL a reset email points at.

    Built from FRONTEND_URL rather than the request, because the API and the
    storefront are different origins and the API renders no shopper pages.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    base = settings.FRONTEND_URL.rstrip("/")
    return f"{base}/account/reset-password?uid={uid}&token={token}"


def send_password_reset_email(user, locale=DEFAULT_LOCALE):
    """Mail `user` a reset link, and never let a delivery failure surface.

    The caller returns the same neutral response whatever happens here — an
    error that reached the client would undo the whole point of that response,
    turning "the send failed" into "this address has an account".
    """
    if locale not in SUPPORTED_LOCALES:
        locale = DEFAULT_LOCALE

    context = {
        "user": user,
        "reset_link": build_password_reset_link(user),
        "expiry_hours": settings.PASSWORD_RESET_TIMEOUT // 3600,
    }
    message = EmailMultiAlternatives(
        subject=RESET_SUBJECTS[locale],
        body=render_to_string(f"accounts/emails/password_reset.{locale}.txt", context),
        to=[user.email],
    )
    message.attach_alternative(
        render_to_string(f"accounts/emails/password_reset.{locale}.html", context),
        "text/html",
    )

    try:
        message.send()
    except Exception:
        # The only production signal this feature has — the caller returns a
        # neutral 200 no matter what happens here, so this log line is the
        # one place a failed send is visible at all. Include enough to act on
        # it without a debugger: who it was for and which template rendered.
        logger.exception(
            "Password reset email failed for user %s <%s> (locale=%s)",
            user.pk,
            user.email,
            locale,
        )


def load_user_from_reset(uid, token):
    """The user a (uid, token) pair names, or None if the pair is no good.

    Shared by the verify and confirm endpoints so the two cannot disagree about
    what a valid link is — a link that verifies and then fails on submit is the
    exact bug this prevents.
    """
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError, UnicodeDecodeError):
        return None

    if not default_token_generator.check_token(user, token):
        return None
    return user


def revoke_refresh_tokens(user):
    """Blacklist every refresh token this user still holds.

    JWTs are stateless, so without this a password reset leaves whoever stole
    the account still signed in — which is the one thing the reset was for.
    """
    for outstanding in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=outstanding)
