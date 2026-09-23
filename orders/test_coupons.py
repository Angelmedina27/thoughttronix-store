"""Coupons at the view layer: applying/removing on the cart, and the
checkout page's guarantee that a bad code never reaches the customer as a
crash — only ever a redirect with a clean message."""

from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.urls import reverse
from django.utils import timezone

from .models import Order
from .test_checkout_form import VALID_DATA

pytestmark = pytest.mark.django_db


# --- Applying and removing on the cart page -----------------------------------


def test_applying_a_valid_code_attaches_it_to_the_cart(
    client, customer, cart, cart_item, coupon
):
    client.force_login(customer)

    response = client.post(
        reverse("orders:apply_coupon"), {"coupon_code": "fall26"}, follow=True
    )

    cart.refresh_from_db()
    assert cart.coupon_code == "FALL26"
    assert "applied" in response.content.decode()


def test_applying_an_invalid_code_shows_a_clean_message_not_a_crash(
    client, customer, cart, cart_item
):
    client.force_login(customer)

    response = client.post(
        reverse("orders:apply_coupon"), {"coupon_code": "NOPE"}, follow=True
    )

    assert response.status_code == HTTPStatus.OK
    assert "recognized" in response.content.decode()
    cart.refresh_from_db()
    assert cart.coupon_code == ""


def test_removing_a_code_clears_it(client, customer, cart, cart_item, coupon):
    cart.coupon_code = coupon.code
    cart.save()
    client.force_login(customer)

    client.post(reverse("orders:apply_coupon"), {"coupon_code": ""})

    cart.refresh_from_db()
    assert cart.coupon_code == ""


def test_cart_page_shows_the_discount_once_applied(
    client, customer, cart, cart_item, coupon
):
    cart.coupon_code = coupon.code
    cart.save()
    client.force_login(customer)

    page = client.get(reverse("orders:cart")).content.decode()

    assert "FALL26" in page
    assert "559.98" in page  # 699.98 - 20%


# --- Checkout: a bad code never crashes checkout --------------------------------


def test_checkout_with_a_retired_coupon_redirects_with_a_message_not_a_500(
    client, customer, cart, cart_item, coupon
):
    coupon.is_active = False
    coupon.save()
    cart.coupon_code = coupon.code
    cart.save()
    client.force_login(customer)

    response = client.get(reverse("orders:checkout"))

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("orders:cart")
    cart.refresh_from_db()
    assert cart.coupon_code == ""


def test_checkout_with_an_expired_coupon_redirects_with_a_message_not_a_500(
    client, customer, cart, cart_item, coupon
):
    coupon.expires_at = timezone.now() - timedelta(days=1)
    coupon.save()
    cart.coupon_code = coupon.code
    cart.save()
    client.force_login(customer)

    response = client.get(reverse("orders:checkout"), follow=True)

    assert "expired" in response.content.decode()


def test_a_successful_checkout_applies_the_discount_and_records_the_coupon(
    client, customer, cart, cart_item, coupon
):
    cart.coupon_code = coupon.code
    cart.save()
    client.force_login(customer)

    client.post(reverse("orders:checkout"), VALID_DATA, follow=True)

    order = Order.objects.get(user=customer)
    assert order.coupon_code == "FALL26"
    assert order.discount_amount == Decimal("140.00")
    assert order.total == Decimal("559.98")
    cart.refresh_from_db()
    assert cart.coupon_code == ""
