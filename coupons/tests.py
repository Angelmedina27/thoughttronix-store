"""Coupon model behavior: normalization, validation, and usability."""

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Coupon

pytestmark = pytest.mark.django_db


def test_the_code_is_uppercased_on_save():
    coupon = Coupon.objects.create(code="fall26", percent_off=20)

    assert coupon.code == "FALL26"


@pytest.mark.parametrize("code", ["FALL 26", "fall-26", "fall_26", "fall26!"])
def test_codes_with_spaces_or_punctuation_are_rejected(code):
    coupon = Coupon(code=code.upper(), percent_off=20)

    with pytest.raises(ValidationError):
        coupon.full_clean()


@pytest.mark.parametrize("percent_off", [0, -5, 101])
def test_percent_off_must_be_between_1_and_100(percent_off):
    coupon = Coupon(code="FALL26", percent_off=percent_off)

    with pytest.raises(ValidationError):
        coupon.full_clean()


def test_a_coupon_with_no_expiry_never_expires():
    coupon = Coupon.objects.create(code="FALL26", percent_off=20)

    assert not coupon.is_expired()
    assert coupon.is_usable()


def test_a_past_expires_at_is_expired():
    coupon = Coupon.objects.create(
        code="FALL26", percent_off=20, expires_at=timezone.now() - timedelta(days=1)
    )

    assert coupon.is_expired()
    assert not coupon.is_usable()


def test_a_retired_coupon_is_not_usable_even_if_not_expired():
    coupon = Coupon.objects.create(code="FALL26", percent_off=20, is_active=False)

    assert not coupon.is_expired()
    assert not coupon.is_usable()


def test_scope_display_reflects_order_wide_vs_product(product):
    order_wide = Coupon.objects.create(code="FALL26", percent_off=20)
    product_specific = Coupon.objects.create(
        code="SERAPHINE15", percent_off=15, product=product
    )

    assert order_wide.scope_display == "Order-wide"
    assert product_specific.scope_display == product.name
