import pytest
from django.core import mail

from apps.accounts.services import build_password_reset_link, send_password_reset_email

pytestmark = pytest.mark.django_db


def test_link_points_at_the_frontend_reset_route(user, settings):
    settings.FRONTEND_URL = "https://shop.example.com"

    link = build_password_reset_link(user)

    assert link.startswith("https://shop.example.com/account/reset-password?uid=")
    assert "&token=" in link


def test_link_does_not_double_the_slash_when_frontend_url_has_a_trailing_one(user, settings):
    settings.FRONTEND_URL = "https://shop.example.com/"

    assert "https://shop.example.com/account/reset-password" in build_password_reset_link(user)


def test_send_delivers_one_mail_carrying_the_link(user):
    send_password_reset_email(user)

    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.to == [user.email]
    assert "/account/reset-password?uid=" in sent.body


def test_send_attaches_an_html_alternative(user):
    send_password_reset_email(user)

    content_types = [content_type for _, content_type in mail.outbox[0].alternatives]
    assert "text/html" in content_types


def test_send_uses_the_arabic_template_for_an_arabic_locale(user):
    send_password_reset_email(user, "ar")

    assert "كلمة المرور" in mail.outbox[0].body


def test_send_falls_back_to_english_for_an_unsupported_locale(user):
    send_password_reset_email(user, "fr")

    assert "reset" in mail.outbox[0].body.lower()


def test_send_swallows_and_logs_a_provider_failure(user, monkeypatch, caplog):
    def explode(self, *args, **kwargs):
        raise RuntimeError("Brevo is down")

    monkeypatch.setattr("django.core.mail.EmailMultiAlternatives.send", explode)

    send_password_reset_email(user)  # must not raise

    assert "Brevo is down" in caplog.text
