"""Account security: the cross-cutting logic behind the Security Center.

The third deliberate deep module. It owns the security alerts — emails
telling an account's owner that a credential changed — and the two
brute-force throttles: the sign-in lockout and the reset-email rate limit.
Views call in here to send alerts; forms call in here to throttle. Neither
builds emails or touches the throttle counters themselves.

The throttles count in Django's cache. The default in-memory cache needs
no configuration, but its counters reset when the server restarts and are
not shared between server processes — a documented limitation.
"""

import hashlib
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from .models import User

LOGIN_FAILURE_LIMIT = 5
LOGIN_FAILURE_WINDOW = 15 * 60  # seconds
LOGIN_LOCKOUT = 15 * 60  # seconds
LOCKOUT_MESSAGE = f"Too many attempts — try again in {LOGIN_LOCKOUT // 60} minutes."

RESET_EMAIL_LIMIT = 3
RESET_EMAIL_WINDOW = 60 * 60  # seconds


# --- Login throttle ----------------------------------------------------------


def login_allowed(username: str, ip: str) -> bool:
    """Whether ``username`` may attempt to sign in from ``ip`` right now.

    False while the pair is locked out — even a correct password is turned
    away. Counting per username *and* address means an attacker failing as
    someone else can't lock the real owner out from their own network.
    """
    return cache.get(_login_key("lockout", username, ip)) is None


def record_login_failure(username: str, ip: str) -> bool:
    """Count one failed sign-in for ``username`` from ``ip``.

    Failures are counted in a fixed window of ``LOGIN_FAILURE_WINDOW``
    seconds that opens with the first one. The ``LOGIN_FAILURE_LIMIT``-th
    failure in a window locks the pair out for ``LOGIN_LOCKOUT`` seconds;
    when the lockout lifts, counting starts again from zero.

    Returns whether this failure triggered the lockout.
    """
    failures_key = _login_key("failures", username, ip)
    cache.add(failures_key, 0, LOGIN_FAILURE_WINDOW)
    try:
        failures = cache.incr(failures_key)
    except ValueError:
        # The window closed between add() and incr(); this failure opens
        # a new one.
        cache.set(failures_key, 1, LOGIN_FAILURE_WINDOW)
        failures = 1
    if failures < LOGIN_FAILURE_LIMIT:
        return False
    cache.set(_login_key("lockout", username, ip), True, LOGIN_LOCKOUT)
    cache.delete(failures_key)
    return True


def clear_login_failures(username: str, ip: str) -> None:
    """Forget ``username``'s failed sign-ins from ``ip`` after a success,
    so an earlier typo doesn't count against a later attempt."""
    cache.delete(_login_key("failures", username, ip))


def _login_key(kind: str, username: str, ip: str) -> str:
    # Hashed so any username is a safe cache key.
    digest = hashlib.sha256(f"{username}|{ip}".encode()).hexdigest()
    return f"accounts:login-{kind}:{digest}"


# --- Reset-email throttle ----------------------------------------------------


def allow_reset_email(email: str) -> bool:
    """Decide whether another password-reset email may go to ``email``, and
    count it if so.

    At most ``RESET_EMAIL_LIMIT`` per address in a fixed window of
    ``RESET_EMAIL_WINDOW`` seconds, so the forgot-password form can't be
    used to flood an inbox. Addresses are compared ignoring case.
    """
    digest = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    key = f"accounts:reset-emails:{digest}"
    cache.add(key, 0, RESET_EMAIL_WINDOW)
    try:
        sent = cache.incr(key)
    except ValueError:
        cache.set(key, 1, RESET_EMAIL_WINDOW)
        sent = 1
    return sent <= RESET_EMAIL_LIMIT


# --- Security alerts ---------------------------------------------------------


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
        recipient=user.email,
        subject="Your ThoughtTronix password was changed",
        template_name="accounts/email/password_changed.txt",
        changed_at=user.password_changed_at,
    )


def send_email_changed_alert(user: User, old_email: str, request: HttpRequest) -> bool:
    """Tell the *previous* address that ``user``'s email was just changed.

    The alert goes to ``old_email``, not the new address: if someone else
    redirected the account, the real owner is the one still reading the
    old inbox. Nothing is sent when there was no previous email, or when
    the address didn't actually change.

    Returns whether an email was sent.
    """
    if old_email == user.email:
        return False
    return _send_alert(
        user,
        request,
        recipient=old_email,
        subject="Your ThoughtTronix email address was changed",
        template_name="accounts/email/email_changed.txt",
        changed_at=None,
    )


def send_password_reset_alert(user: User, request: HttpRequest) -> bool:
    """Tell ``user`` their password was just reset through the forgot-password
    loop.

    A reset the owner didn't request means someone else controls their
    inbox or their reset link, so the email says when it happened and
    links straight to a fresh reset. Accounts with no email on file are
    skipped — though without one they can't reach the reset loop anyway.

    Returns whether an email was sent.
    """
    return _send_alert(
        user,
        request,
        recipient=user.email,
        subject="Your ThoughtTronix password was reset",
        template_name="accounts/email/password_reset_completed.txt",
        changed_at=user.password_changed_at,
    )


def _send_alert(
    user: User,
    request: HttpRequest,
    *,
    recipient: str,
    subject: str,
    template_name: str,
    changed_at: datetime | None,
) -> bool:
    if not recipient:
        return False
    body = render_to_string(
        template_name,
        {
            "user": user,
            "changed_at": changed_at or timezone.now(),
            "login_url": request.build_absolute_uri(reverse("accounts:login")),
            "reset_url": request.build_absolute_uri(reverse("accounts:password_reset")),
        },
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient])
    return True
