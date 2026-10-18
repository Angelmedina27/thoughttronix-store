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
