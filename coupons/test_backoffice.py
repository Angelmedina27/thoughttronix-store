"""Back-office coupon management: access control, CRUD, and retiring."""

from http import HTTPStatus

import pytest
from django.urls import reverse

from .models import Coupon

pytestmark = pytest.mark.django_db


def manage_urls(coupon):
    return [
        reverse("coupons:manage_coupons"),
        reverse("coupons:manage_coupon_create"),
        reverse("coupons:manage_coupon_update", kwargs={"pk": coupon.pk}),
        reverse("coupons:manage_coupon_retire", kwargs={"pk": coupon.pk}),
    ]


def coupon_data(**overrides):
    data = {"code": "WINTER26", "percent_off": "10", "is_active": "on"}
    data.update(overrides)
    return data


# --- Access control ----------------------------------------------------------


def test_anonymous_users_are_sent_to_login(client, coupon):
    for url in manage_urls(coupon):
        response = client.get(url)

        assert response.status_code == HTTPStatus.FOUND, url
        assert reverse("accounts:login") in response.url


def test_customers_get_403(client, customer, coupon):
    client.force_login(customer)

    for url in manage_urls(coupon):
        assert client.get(url).status_code == HTTPStatus.FORBIDDEN, url


def test_staff_can_view_list_create_and_edit(client, staff_user, coupon):
    client.force_login(staff_user)

    for url in [
        reverse("coupons:manage_coupons"),
        reverse("coupons:manage_coupon_create"),
        reverse("coupons:manage_coupon_update", kwargs={"pk": coupon.pk}),
    ]:
        assert client.get(url).status_code == HTTPStatus.OK, url


# --- CRUD and retiring ---------------------------------------------------------


def test_staff_can_create_an_order_wide_coupon(client, staff_user):
    client.force_login(staff_user)

    client.post(reverse("coupons:manage_coupon_create"), coupon_data())

    coupon = Coupon.objects.get(code="WINTER26")
    assert coupon.percent_off == 10
    assert coupon.product is None
    assert coupon.is_active


def test_staff_can_create_a_product_specific_coupon(client, staff_user, product):
    client.force_login(staff_user)

    client.post(
        reverse("coupons:manage_coupon_create"),
        coupon_data(product=str(product.pk)),
    )

    coupon = Coupon.objects.get(code="WINTER26")
    assert coupon.product == product


def test_a_lowercase_code_is_normalized_on_create(client, staff_user):
    client.force_login(staff_user)

    client.post(reverse("coupons:manage_coupon_create"), coupon_data(code="winter26"))

    assert Coupon.objects.filter(code="WINTER26").exists()


def test_staff_can_retire_a_coupon(client, staff_user, coupon):
    client.force_login(staff_user)

    response = client.post(
        reverse("coupons:manage_coupon_retire", kwargs={"pk": coupon.pk})
    )

    coupon.refresh_from_db()
    assert not coupon.is_active
    assert response.url == reverse("coupons:manage_coupons")


def test_retiring_does_not_delete_the_coupon(client, staff_user, coupon):
    client.force_login(staff_user)

    client.post(reverse("coupons:manage_coupon_retire", kwargs={"pk": coupon.pk}))

    assert Coupon.objects.filter(pk=coupon.pk).exists()


def test_list_has_a_designed_empty_state(client, staff_user):
    client.force_login(staff_user)

    page = client.get(reverse("coupons:manage_coupons")).content.decode()

    assert "No coupons yet" in page


def test_list_shows_active_and_retired_status(client, staff_user, coupon):
    client.force_login(staff_user)
    coupon.is_active = False
    coupon.save()

    page = client.get(reverse("coupons:manage_coupons")).content.decode()

    assert "Retired" in page
