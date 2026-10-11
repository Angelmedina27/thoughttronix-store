import re
import time
from datetime import datetime, timedelta
from http import HTTPStatus

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse
from django.utils import dateformat, timezone

from accounts import security

# --- Signup -----------------------------------------------------------------


def test_signup_page_returns_200(client, db):
    response = client.get(reverse("accounts:signup"))

    assert response.status_code == HTTPStatus.OK


def test_signup_creates_plain_customer(client, db):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "fresh-thinker",
            "email": "fresh@example.com",
            "password1": "neural-implant-9000",
            "password2": "neural-implant-9000",
        },
        follow=True,
    )

    user = get_user_model().objects.get(username="fresh-thinker")
    assert not user.is_staff
    assert not user.is_superuser

    # Signup hands off to the login page with a confirmation message;
    # auto-login is a student exercise, so the visitor is still anonymous.
    assert response.redirect_chain[-1][0] == reverse("accounts:login")
    assert "Account created" in response.content.decode()
    assert not response.context["user"].is_authenticated


def test_signup_password_mismatch_shows_field_error(client, db):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "fresh-thinker",
            "email": "fresh@example.com",
            "password1": "neural-implant-9000",
            "password2": "neural-implant-9001",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["password2"]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


def signup_data(**overrides):
    return {
        "username": "fresh-thinker",
        "email": "fresh@example.com",
        "password1": "neural-implant-9000",
        "password2": "neural-implant-9000",
    } | overrides


def test_signup_requires_email(client, db):
    response = client.post(reverse("accounts:signup"), signup_data(email=""))

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["email"]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


def test_signup_stores_email_trimmed_and_lowercased(client, db):
    client.post(reverse("accounts:signup"), signup_data(email="  Fresh@Example.COM "))

    user = get_user_model().objects.get(username="fresh-thinker")
    assert user.email == "fresh@example.com"


@pytest.mark.parametrize("email", ["casey@example.com", "Casey@EXAMPLE.com"])
def test_signup_rejects_email_in_use_in_any_case(client, customer, email):
    customer.email = "casey@example.com"
    customer.save()

    response = client.post(reverse("accounts:signup"), signup_data(email=email))

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["email"] == [
        "An account with this email already exists."
    ]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


# --- User model: email rules and password_changed_at -------------------------


def test_email_is_normalized_on_save(db):
    user = get_user_model().objects.create_user(
        username="bob", email="  Bob@Example.com ", password="x"
    )

    user.refresh_from_db()
    assert user.email == "bob@example.com"


def test_database_rejects_emails_differing_only_by_case(db):
    User = get_user_model()
    User.objects.create_user(username="bob", email="bob@example.com")

    # Bypass save() normalization: the constraint itself must catch it.
    with pytest.raises(IntegrityError):
        User.objects.bulk_create([User(username="bob2", email="BOB@example.com")])


def test_database_allows_many_blank_emails(db):
    User = get_user_model()
    User.objects.create_user(username="old-timer-1")
    User.objects.create_user(username="old-timer-2", email="")

    assert User.objects.filter(email="").count() == 2


def test_email_in_use_ignores_case_blanks_and_own_account(customer):
    User = get_user_model()
    customer.email = "casey@example.com"
    customer.save()

    assert User.objects.email_in_use("CASEY@example.com")
    assert not User.objects.email_in_use("casey@example.com", exclude_pk=customer.pk)
    assert not User.objects.email_in_use("")


def test_creating_a_user_leaves_password_changed_at_null(customer):
    customer.refresh_from_db()

    assert customer.password_changed_at is None


def test_set_password_on_saved_user_stamps_password_changed_at(customer):
    customer.set_password("brand-new-thoughts-42")
    customer.save()

    customer.refresh_from_db()
    assert customer.password_changed_at is not None


# --- Login and logout --------------------------------------------------------


def test_login_page_returns_200(client, db):
    response = client.get(reverse("accounts:login"))

    assert response.status_code == HTTPStatus.OK


def test_login_round_trip(client, customer):
    response = client.post(
        reverse("accounts:login"),
        {"username": "customer", "password": "customer123"},
        follow=True,
    )

    assert response.redirect_chain[-1][0] == reverse("products:catalog")
    assert response.context["user"] == customer


def test_login_bad_credentials_stays_put(client, customer):
    response = client.post(
        reverse("accounts:login"),
        {"username": "customer", "password": "wrong"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].non_field_errors()


def test_logout_signs_out_with_message(client, customer):
    client.force_login(customer)

    response = client.post(reverse("accounts:logout"), follow=True)

    assert response.redirect_chain[-1][0] == reverse("products:catalog")
    assert "You have signed out." in response.content.decode()
    assert not response.context["user"].is_authenticated


# --- Auth-aware navbar --------------------------------------------------------


def test_navbar_offers_login_and_signup_to_visitors(client, db):
    page = client.get(reverse("products:catalog")).content.decode()

    assert reverse("accounts:login") in page
    assert reverse("accounts:signup") in page
    assert "Sign out" not in page


def test_navbar_greets_signed_in_customer(client, customer):
    client.force_login(customer)

    page = client.get(reverse("products:catalog")).content.decode()

    assert "Hi, customer" in page
    assert "Sign out" in page
    assert reverse("accounts:signup") not in page


# --- Security Center hub ------------------------------------------------------


def test_security_center_redirects_anonymous_visitors_to_sign_in(client, db):
    url = reverse("accounts:security")

    response = client.get(url)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"


@pytest.mark.parametrize("role", ["customer", "staff_user", "admin_user"])
def test_security_center_is_open_to_every_role(client, request, role):
    client.force_login(request.getfixturevalue(role))

    response = client.get(reverse("accounts:security"))

    assert response.status_code == HTTPStatus.OK


def test_security_center_shows_account_details(client, customer):
    customer.email = "casey@example.com"
    customer.save()
    client.login(username="customer", password="customer123")
    customer.refresh_from_db()

    page = client.get(reverse("accounts:security")).content.decode()

    assert "casey@example.com" in page
    assert "Last sign-in" in page
    assert dateformat.format(customer.last_login, "M j, Y") in page
    assert "Member since" in page
    assert dateformat.format(customer.date_joined, "M j, Y") in page
    assert "no email on file" not in page.lower()


def test_security_center_says_password_never_changed(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert "Never changed since signup" in page


def test_security_center_shows_when_password_last_changed(client, customer):
    changed_at = timezone.now() - timedelta(days=21)
    get_user_model().objects.filter(pk=customer.pk).update(
        password_changed_at=changed_at
    )
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert dateformat.format(changed_at, "M j, Y") in page
    assert "3\xa0weeks ago" in page
    assert "Never changed since signup" not in page


def test_security_center_warns_accounts_without_an_email(client, customer):
    assert customer.email == ""
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert "Your account has no email on file." in page


def test_navbar_offers_account_security_to_signed_in_users_only(client, customer):
    url = reverse("accounts:security")
    assert url not in client.get(reverse("products:catalog")).content.decode()

    client.force_login(customer)
    page = client.get(reverse("products:catalog")).content.decode()

    assert url in page
    assert "Account security" in page


# --- Change password ----------------------------------------------------------


def password_change_data(**overrides):
    return {
        "old_password": "customer123",
        "new_password1": "brand-new-thoughts-42",
        "new_password2": "brand-new-thoughts-42",
        **overrides,
    }


def test_change_password_redirects_anonymous_visitors_to_sign_in(client, db):
    url = reverse("accounts:password_change")

    response = client.get(url)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"


def test_security_center_links_to_change_password(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert reverse("accounts:password_change") in page


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"old_password": "not-my-password"}, "old_password"),
        ({"new_password2": "brand-new-thoughts-43"}, "new_password2"),
        ({"new_password1": "12345678", "new_password2": "12345678"}, "new_password2"),
    ],
    ids=["wrong-current", "mismatch", "fails-validators"],
)
def test_change_password_rejects_bad_input(
    client, customer, mailoutbox, overrides, field
):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:password_change"), password_change_data(**overrides)
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors[field]
    customer.refresh_from_db()
    assert customer.check_password("customer123")
    assert customer.password_changed_at is None
    assert mailoutbox == []


def test_change_password_succeeds_and_returns_to_hub(client, customer):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:password_change"), password_change_data(), follow=True
    )

    assert response.redirect_chain[-1][0] == reverse("accounts:security")
    page = response.content.decode()
    assert "Your password has been changed." in page
    assert "Never changed since signup" not in page
    customer.refresh_from_db()
    assert customer.check_password("brand-new-thoughts-42")
    assert customer.password_changed_at is not None


def test_change_password_keeps_this_session_and_ends_the_others(client, customer):
    other_device = Client()
    other_device.login(username="customer", password="customer123")
    client.login(username="customer", password="customer123")
    hub = reverse("accounts:security")

    client.post(reverse("accounts:password_change"), password_change_data())

    assert client.get(hub).status_code == HTTPStatus.OK
    assert other_device.get(hub).status_code == HTTPStatus.FOUND


def test_change_password_sends_alert_to_the_account_email(client, customer, mailoutbox):
    customer.email = "casey@example.com"
    customer.save()
    client.force_login(customer)

    client.post(reverse("accounts:password_change"), password_change_data())

    assert len(mailoutbox) == 1
    alert = mailoutbox[0]
    assert alert.to == ["casey@example.com"]
    assert alert.from_email == settings.DEFAULT_FROM_EMAIL
    assert "password" in alert.subject.lower()
    customer.refresh_from_db()
    assert dateformat.format(customer.password_changed_at, "M j, Y") in alert.body
    assert "If you didn't" in alert.body
    assert "http://testserver" + reverse("accounts:login") in alert.body


def test_change_password_sends_no_alert_without_an_email(client, customer, mailoutbox):
    assert customer.email == ""
    client.force_login(customer)

    response = client.post(reverse("accounts:password_change"), password_change_data())

    assert response.status_code == HTTPStatus.FOUND
    assert mailoutbox == []


def test_default_from_email_has_the_documented_default():
    assert settings.DEFAULT_FROM_EMAIL == "ThoughtTronix <no-reply@thoughttronix.local>"


# --- Change email -------------------------------------------------------------


def email_change_data(**overrides):
    return {
        "email": "casey@example.com",
        "current_password": "customer123",
        **overrides,
    }


def test_change_email_redirects_anonymous_visitors_to_sign_in(client, db):
    url = reverse("accounts:email_change")

    response = client.get(url)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"


def test_security_center_links_to_change_email(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert reverse("accounts:email_change") in page


def test_change_email_rejects_a_wrong_current_password(client, customer, mailoutbox):
    customer.email = "old@example.com"
    customer.save()
    client.force_login(customer)

    response = client.post(
        reverse("accounts:email_change"),
        email_change_data(current_password="not-my-password"),
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["current_password"]
    customer.refresh_from_db()
    assert customer.email == "old@example.com"
    assert mailoutbox == []


def test_change_email_rejects_another_accounts_email_in_any_case(
    client, customer, staff_user, mailoutbox
):
    staff_user.email = "taken@example.com"
    staff_user.save()
    client.force_login(customer)

    response = client.post(
        reverse("accounts:email_change"), email_change_data(email="TAKEN@Example.com")
    )

    assert response.status_code == HTTPStatus.OK
    assert "already exists" in response.context["form"].errors["email"][0]
    customer.refresh_from_db()
    assert customer.email == ""
    assert mailoutbox == []


def test_change_email_accepts_re_entering_ones_own_email(client, customer, mailoutbox):
    customer.email = "casey@example.com"
    customer.save()
    client.force_login(customer)

    response = client.post(
        reverse("accounts:email_change"), email_change_data(email="Casey@Example.com")
    )

    assert response.status_code == HTTPStatus.FOUND
    customer.refresh_from_db()
    assert customer.email == "casey@example.com"
    assert mailoutbox == []


def test_change_email_stores_normalized_email_and_returns_to_hub(client, customer):
    customer.email = "old@example.com"
    customer.save()
    client.force_login(customer)

    response = client.post(
        reverse("accounts:email_change"),
        email_change_data(email="  New.Casey@Example.COM "),
        follow=True,
    )

    assert response.redirect_chain[-1][0] == reverse("accounts:security")
    page = response.content.decode()
    assert "Your email has been updated." in page
    assert "new.casey@example.com" in page
    customer.refresh_from_db()
    assert customer.email == "new.casey@example.com"


def test_change_email_sends_alert_to_the_old_address(client, customer, mailoutbox):
    customer.email = "old@example.com"
    customer.save()
    client.force_login(customer)

    client.post(reverse("accounts:email_change"), email_change_data())

    assert len(mailoutbox) == 1
    alert = mailoutbox[0]
    assert alert.to == ["old@example.com"]
    assert alert.from_email == settings.DEFAULT_FROM_EMAIL
    assert "email" in alert.subject.lower()
    assert "casey@example.com" in alert.body
    assert dateformat.format(timezone.now(), "M j, Y") in alert.body
    assert "If you didn't" in alert.body
    assert "http://testserver" + reverse("accounts:login") in alert.body


def test_adding_a_first_email_sends_no_alert_and_clears_the_warning(
    client, customer, mailoutbox
):
    assert customer.email == ""
    client.force_login(customer)

    response = client.post(
        reverse("accounts:email_change"), email_change_data(), follow=True
    )

    assert mailoutbox == []
    assert "no email on file" not in response.content.decode()
    customer.refresh_from_db()
    assert customer.email == "casey@example.com"


# --- Forgot password ----------------------------------------------------------


RESET_LINK = re.compile(r"http://testserver(/accounts/password/reset/[^\s]+/)")


@pytest.fixture
def casey(customer):
    """The ``customer`` fixture with an email on file, so it can reset."""
    customer.email = "casey@example.com"
    customer.save()
    return customer


def request_reset_link(client, mailoutbox, email="casey@example.com"):
    """Request a reset email and return the path of the link inside it."""
    client.post(reverse("accounts:password_reset"), {"email": email})
    return RESET_LINK.search(mailoutbox[-1].body).group(1)


def strip_csrf(response):
    return re.sub(r'"X-CSRFToken": "[^"]*"', "", response.content.decode())


def new_password_data(**overrides):
    return {
        "new_password1": "brand-new-thoughts-42",
        "new_password2": "brand-new-thoughts-42",
        **overrides,
    }


def test_login_page_links_to_password_reset(client, db):
    page = client.get(reverse("accounts:login")).content.decode()

    assert "Forgot password?" in page
    assert reverse("accounts:password_reset") in page


def test_password_reset_page_returns_200(client, db):
    response = client.get(reverse("accounts:password_reset"))

    assert response.status_code == HTTPStatus.OK


def test_reset_request_responds_the_same_for_known_and_unknown_emails(
    client, casey, mailoutbox
):
    url = reverse("accounts:password_reset")

    known = client.post(url, {"email": "casey@example.com"}, follow=True)
    unknown = client.post(url, {"email": "nobody@example.com"}, follow=True)

    assert known.redirect_chain == unknown.redirect_chain
    assert known.redirect_chain[-1][0] == reverse("accounts:password_reset_done")
    # The CSRF token is masked afresh on every render; blank it out.
    assert strip_csrf(known) == strip_csrf(unknown)
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["casey@example.com"]


def test_reset_request_matches_email_in_any_case(client, casey, mailoutbox):
    client.post(reverse("accounts:password_reset"), {"email": "Casey@Example.COM"})

    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["casey@example.com"]


def test_reset_done_page_states_expiry_and_suggests_spam(client, db):
    page = client.get(reverse("accounts:password_reset_done")).content.decode()

    assert "If an account exists for that email" in page
    assert "1 hour" in page
    assert "spam" in page


def test_reset_email_contains_a_working_link(client, casey, mailoutbox):
    link = request_reset_link(client, mailoutbox)

    email = mailoutbox[0]
    assert email.from_email == settings.DEFAULT_FROM_EMAIL
    assert "reset" in email.subject.lower()
    assert "1 hour" in email.body
    response = client.get(link, follow=True)
    assert response.status_code == HTTPStatus.OK
    assert response.context["validlink"] is True
    assert "form" in response.context


def test_reset_rejects_a_password_that_fails_the_validators(client, casey, mailoutbox):
    link = request_reset_link(client, mailoutbox)
    form_url = client.get(link).url

    response = client.post(
        form_url, new_password_data(new_password1="12345678", new_password2="12345678")
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["new_password2"]
    casey.refresh_from_db()
    assert casey.check_password("customer123")


def test_reset_completes_and_hands_off_to_sign_in(client, casey, mailoutbox):
    link = request_reset_link(client, mailoutbox)
    form_url = client.get(link).url

    response = client.post(form_url, new_password_data(), follow=True)

    assert response.redirect_chain[-1][0] == reverse("accounts:login")
    assert "Your password has been reset" in response.content.decode()
    assert not response.context["user"].is_authenticated
    casey.refresh_from_db()
    assert casey.check_password("brand-new-thoughts-42")
    assert casey.password_changed_at is not None


def test_reset_signs_out_every_other_session(client, casey, mailoutbox):
    other_device = Client()
    other_device.login(username="customer", password="customer123")
    hub = reverse("accounts:security")
    assert other_device.get(hub).status_code == HTTPStatus.OK

    link = request_reset_link(client, mailoutbox)
    client.post(client.get(link).url, new_password_data())

    assert other_device.get(hub).status_code == HTTPStatus.FOUND


def test_reset_sends_the_reset_alert(client, casey, mailoutbox):
    link = request_reset_link(client, mailoutbox)

    client.post(client.get(link).url, new_password_data())

    assert len(mailoutbox) == 2
    alert = mailoutbox[1]
    assert alert.to == ["casey@example.com"]
    assert alert.subject == "Your ThoughtTronix password was reset"
    casey.refresh_from_db()
    assert dateformat.format(casey.password_changed_at, "M j, Y") in alert.body
    assert "If you didn't" in alert.body
    assert "http://testserver" + reverse("accounts:password_reset") in alert.body


def test_used_reset_link_shows_the_invalid_link_message(client, casey, mailoutbox):
    link = request_reset_link(client, mailoutbox)
    client.post(client.get(link).url, new_password_data())

    response = Client().get(link, follow=True)

    assert response.context["validlink"] is False
    page = response.content.decode()
    assert "invalid or has expired" in page
    assert reverse("accounts:password_reset") in page


def test_expired_reset_link_shows_the_invalid_link_message(
    client, casey, mailoutbox, settings, monkeypatch
):
    settings.PASSWORD_RESET_TIMEOUT = 60
    link = request_reset_link(client, mailoutbox)
    # Step the token generator's clock past the (overridden) timeout.
    later = datetime.now() + timedelta(seconds=61)
    monkeypatch.setattr(PasswordResetTokenGenerator, "_now", lambda self: later)

    response = client.get(link, follow=True)

    assert response.context["validlink"] is False
    assert "invalid or has expired" in response.content.decode()
    casey.refresh_from_db()
    assert casey.check_password("customer123")


def test_password_reset_timeout_has_the_documented_default():
    assert settings.PASSWORD_RESET_TIMEOUT == 3600


# --- Brute-force protection: the security module ------------------------------


def fail_logins(times, username="customer", ip="10.0.0.1"):
    for _ in range(times):
        security.record_login_failure(username, ip)


def test_login_is_allowed_until_the_fifth_failure():
    fail_logins(4)
    assert security.login_allowed("customer", "10.0.0.1")

    assert security.record_login_failure("customer", "10.0.0.1") is True
    assert not security.login_allowed("customer", "10.0.0.1")


def test_login_failures_count_per_username_and_ip():
    fail_logins(5)

    assert not security.login_allowed("customer", "10.0.0.1")
    assert security.login_allowed("customer", "10.0.0.2")
    assert security.login_allowed("employee", "10.0.0.1")


def test_clearing_login_failures_starts_the_count_again():
    fail_logins(4)

    security.clear_login_failures("customer", "10.0.0.1")
    fail_logins(4)

    assert security.login_allowed("customer", "10.0.0.1")


def test_login_lockout_expires(monkeypatch):
    fail_logins(5)
    later = time.time() + security.LOGIN_LOCKOUT + 1
    monkeypatch.setattr(time, "time", lambda: later)

    assert security.login_allowed("customer", "10.0.0.1")
    # Counting starts again from zero once the lockout lifts.
    fail_logins(4)
    assert security.login_allowed("customer", "10.0.0.1")


def test_reset_emails_are_limited_per_address():
    assert [security.allow_reset_email("casey@example.com") for _ in range(4)] == [
        True,
        True,
        True,
        False,
    ]
    assert not security.allow_reset_email("Casey@Example.com")
    assert security.allow_reset_email("someone-else@example.com")


def test_reset_email_limit_expires(monkeypatch):
    for _ in range(3):
        security.allow_reset_email("casey@example.com")
    later = time.time() + security.RESET_EMAIL_WINDOW + 1
    monkeypatch.setattr(time, "time", lambda: later)

    assert security.allow_reset_email("casey@example.com")


# --- Brute-force protection: sign-in lockout ------------------------------------


def sign_in(client, password, url=None, ip="127.0.0.1", username="customer"):
    return client.post(
        url or reverse("accounts:login"),
        {"username": username, "password": password},
        REMOTE_ADDR=ip,
    )


def test_sixth_sign_in_is_locked_out_even_with_the_right_password(client, customer):
    for _ in range(5):
        sign_in(client, "wrong")

    response = sign_in(client, "customer123")

    assert response.status_code == HTTPStatus.OK
    assert "Too many attempts — try again in 15 minutes." in response.content.decode()
    assert not response.context["user"].is_authenticated


def test_failing_from_another_ip_does_not_lock_out_the_owner(client, customer):
    for _ in range(5):
        sign_in(Client(), "wrong", ip="203.0.113.9")

    response = sign_in(client, "customer123")

    assert response.status_code == HTTPStatus.FOUND
    assert response.wsgi_request.user == customer


def test_successful_sign_in_resets_the_failure_count(client, customer):
    for _ in range(4):
        sign_in(client, "wrong")
    sign_in(client, "customer123")
    client.post(reverse("accounts:logout"))

    for _ in range(4):
        sign_in(client, "wrong")
    response = sign_in(client, "customer123")

    assert response.status_code == HTTPStatus.FOUND


def test_admin_login_is_locked_out_after_five_failures(client, admin_user):
    url = reverse("admin:login")
    for _ in range(5):
        sign_in(client, "wrong", url=url, username="admin")

    response = sign_in(client, "password", url=url, username="admin")

    assert response.status_code == HTTPStatus.OK
    assert "Too many attempts — try again in 15 minutes." in response.content.decode()
    assert client.get(reverse("admin:index")).status_code == HTTPStatus.FOUND


def test_admin_login_still_rejects_non_staff(client, customer):
    response = sign_in(client, "customer123", url=reverse("admin:login"))

    assert response.status_code == HTTPStatus.OK
    assert not response.context["user"].is_authenticated


def test_admin_login_signs_in_staff(client, admin_user):
    response = sign_in(client, "password", url=reverse("admin:login"), username="admin")

    assert response.status_code == HTTPStatus.FOUND
    assert client.get(reverse("admin:index")).status_code == HTTPStatus.OK


# --- Brute-force protection: reset-email rate limit -----------------------------


def test_fourth_reset_request_sends_nothing_but_looks_the_same(
    client, casey, mailoutbox
):
    url = reverse("accounts:password_reset")
    responses = [
        client.post(url, {"email": "casey@example.com"}, follow=True) for _ in range(4)
    ]

    assert len(mailoutbox) == 3
    assert responses[3].redirect_chain == responses[0].redirect_chain
    assert strip_csrf(responses[3]) == strip_csrf(responses[0])
