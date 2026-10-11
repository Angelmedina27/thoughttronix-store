"""Account security: the cross-cutting logic behind the Security Center.

The third deliberate deep module. It owns the security alerts — emails
telling an account's owner that a credential changed — and, in later
phases, the login and reset-email throttles. Views call in here to send
alerts; they never build the emails themselves.
"""

from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .models import User


def send_password_changed_alert(user: User, request: HttpRequest) -> bool:
    """Tell ``user`` their password was just changed from the Security Center.

    The email says what changed, when, and how to recover the account if
    the change wasn't theirs. ``request`` builds absolute links. Accounts
    with no email on file have nowhere to send it, so nothing is sent.

    Returns whether an email was sent.
    """
    return _send_alert(
        user,
        request,
        subject="Your ThoughtTronix password was changed",
        template_name="accounts/email/password_changed.txt",
        changed_at=user.password_changed_at,
    )


def _send_alert(
    user: User,
    request: HttpRequest,
    *,
    subject: str,
    template_name: str,
    changed_at: datetime | None,
) -> bool:
    if not user.email:
        return False
    body = render_to_string(
        template_name,
        {
            "user": user,
            "changed_at": changed_at or timezone.now(),
            "login_url": request.build_absolute_uri(reverse("accounts:login")),
        },
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
    return True
