from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse

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
