"""Back-office reviews: the staff list, its hidden filter, and access control."""

import re
from datetime import timedelta
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from conftest import make_order
from orders.models import Order

from .models import Review

pytestmark = pytest.mark.django_db

LIST_URL = reverse("reviews:manage_reviews")


@pytest.fixture
def hidden_review(product):
    """Another customer's hidden review of ``product``, posted a day ago."""
    author = get_user_model().objects.create_user(username="grumpy", password="x")
    make_order(author, product, Order.Status.DELIVERED)
    return Review.objects.create(
        user=author,
        product=product,
        rating=1,
        comment="It read my mind and told my mother. Never again.",
        is_hidden=True,
        created_at=timezone.now() - timedelta(days=1),
    )


@pytest.fixture
def older_review(review):
    """The ``customer``'s visible review, backdated to a week ago."""
    review.created_at = timezone.now() - timedelta(days=7)
    review.save(update_fields=["created_at"])
    return review


# --- Access control ----------------------------------------------------------


def test_anonymous_users_are_sent_to_login(client):
    response = client.get(LIST_URL)

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


def test_customers_get_403(client, customer):
    client.force_login(customer)

    assert client.get(LIST_URL).status_code == HTTPStatus.FORBIDDEN


def test_the_reviews_tab_is_active(client, staff_user):
    client.force_login(staff_user)

    content = client.get(LIST_URL).content.decode()

    assert re.search(rf'tab-active"\s+href="{LIST_URL}"', content)


# --- The list ----------------------------------------------------------------


def test_the_list_shows_every_review_newest_first(
    client, staff_user, older_review, hidden_review
):
    client.force_login(staff_user)

    content = client.get(LIST_URL).content.decode()

    assert hidden_review.comment in content
    assert older_review.comment in content
    assert content.index(hidden_review.comment) < content.index(older_review.comment)


def test_the_hidden_filter_shows_only_hidden_reviews(
    client, staff_user, review, hidden_review
):
    client.force_login(staff_user)

    content = client.get(LIST_URL, {"hidden": "1"}).content.decode()

    assert hidden_review.comment in content
    assert review.comment not in content


def test_an_empty_list_shows_the_empty_state(client, staff_user):
    client.force_login(staff_user)

    content = client.get(LIST_URL).content.decode()

    assert "No reviews yet" in content


def test_an_empty_hidden_filter_shows_its_own_empty_state(client, staff_user, review):
    client.force_login(staff_user)

    content = client.get(LIST_URL, {"hidden": "1"}).content.decode()

    assert "No hidden reviews" in content
    assert review.comment not in content


# --- Hide / unhide -----------------------------------------------------------


def toggle_url(review):
    return reverse("reviews:toggle_hidden", kwargs={"pk": review.pk})


def test_the_toggle_hides_a_review_and_returns_its_row(client, staff_user, review):
    client.force_login(staff_user)

    response = client.post(toggle_url(review))

    assert response.status_code == HTTPStatus.OK
    assert response.templates[0].name == "reviews/partials/_review_row.html"
    review.refresh_from_db()
    assert review.is_hidden
    content = response.content.decode()
    assert "Unhide" in content
    assert "<html" not in content


def test_the_toggle_unhides_a_hidden_review(client, staff_user, hidden_review):
    client.force_login(staff_user)

    response = client.post(toggle_url(hidden_review))

    hidden_review.refresh_from_db()
    assert not hidden_review.is_hidden
    content = response.content.decode()
    assert "Visible" in content
    assert re.search(r">\s*Hide\s*</button>", content)


def test_the_toggle_never_changes_the_text_or_rating(client, staff_user, review):
    client.force_login(staff_user)

    client.post(
        toggle_url(review), {"rating": "1", "comment": "Staff were here and said so."}
    )

    review.refresh_from_db()
    assert review.rating == 4
    assert review.comment == "Knew what I wanted before I did. Mostly delightful."


def test_the_toggle_is_post_only(client, staff_user, review):
    client.force_login(staff_user)

    response = client.get(toggle_url(review))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    review.refresh_from_db()
    assert not review.is_hidden


def test_customers_cannot_toggle(client, customer, review):
    client.force_login(customer)

    response = client.post(toggle_url(review))

    assert response.status_code == HTTPStatus.FORBIDDEN
    review.refresh_from_db()
    assert not review.is_hidden


def test_anonymous_users_are_sent_to_login_to_toggle(client, review):
    response = client.post(toggle_url(review))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url
    review.refresh_from_db()
    assert not review.is_hidden


def test_toggling_an_unknown_review_is_404(client, staff_user):
    client.force_login(staff_user)

    response = client.post(reverse("reviews:toggle_hidden", kwargs={"pk": 999}))

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_each_row_offers_the_right_toggle(client, staff_user, review, hidden_review):
    client.force_login(staff_user)

    content = client.get(LIST_URL).content.decode()

    assert f'hx-post="{toggle_url(review)}"' in content
    assert f'hx-post="{toggle_url(hidden_review)}"' in content
    assert "Unhide" in content
