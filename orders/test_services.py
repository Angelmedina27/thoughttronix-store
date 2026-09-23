"""place_order tests — coverage priority 3 in the PRD.

Denormalization, cart emptying, atomicity, unavailable rejection, and
the card_last4-only rule.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from products.models import Product

from .models import CartItem, Order, OrderItem
from .services import CouponError, place_order
from .test_checkout_form import VALID_DATA


@pytest.fixture
def checkout_data():
    return dict(VALID_DATA)


def test_creates_an_order_with_denormalized_snapshot(cart, cart_item, checkout_data):
    order = place_order(cart, cart.user, checkout_data)

    assert order.user == cart.user
    assert order.total == Decimal("699.98")
    assert order.status == Order.Status.PLACED
    item = order.items.get()
    assert item.product_name == "Seraphine Home Hub"
    assert item.unit_price == Decimal("349.99")
    assert item.quantity == 2
    assert item.line_total == Decimal("699.98")


def test_order_history_survives_catalog_changes(cart, cart_item, checkout_data):
    order = place_order(cart, cart.user, checkout_data)

    product = cart_item.product
    product.name = "Seraphine Home Hub II"
    product.price = Decimal("999.00")
    product.save()

    item = order.items.get()
    assert item.product_name == "Seraphine Home Hub"
    assert item.unit_price == Decimal("349.99")


def test_addresses_and_email_are_copied_onto_the_order(cart, cart_item, checkout_data):
    order = place_order(cart, cart.user, checkout_data)

    assert order.email == "casey@example.com"
    assert order.shipping_street == "12 Cortex Lane"
    assert order.shipping_line2 == "Unit 7"
    assert order.shipping_state == "TX"
    assert order.billing_zip == "79015-1234"


def test_only_the_last_four_card_digits_are_stored(cart, cart_item, checkout_data):
    order = place_order(cart, cart.user, checkout_data)

    assert order.card_last4 == "4242"
    stored = [field.name for field in Order._meta.get_fields()]
    assert "card_number" not in stored
    assert "card_cvv" not in stored
    assert "card_expiry" not in stored


def test_the_cart_is_emptied(cart, cart_item, checkout_data):
    place_order(cart, cart.user, checkout_data)

    assert not cart.items.exists()
    assert cart.total() == Decimal("0.00")


def test_an_empty_cart_is_rejected(cart, checkout_data):
    with pytest.raises(ValueError):
        place_order(cart, cart.user, checkout_data)

    assert not Order.objects.exists()


def test_an_unavailable_product_is_rejected(
    cart, cart_item, unavailable_product, checkout_data
):
    cart.items.create(product=unavailable_product)

    with pytest.raises(ValueError, match="EchoPatch"):
        place_order(cart, cart.user, checkout_data)

    assert not Order.objects.exists()
    assert cart.items.count() == 2  # the cart is untouched


def test_a_failure_midway_leaves_no_partial_order(
    cart, cart_item, category, checkout_data, monkeypatch
):
    """All-or-nothing: if any line fails, no order and no emptied cart."""
    cart.add(
        Product.objects.create(
            name="Charging Pillow",
            slug="charging-pillow",
            price=Decimal("69.00"),
            category=category,
        )
    )

    original = OrderItem.objects.create
    calls = {"count": 0}

    def create_then_explode(**kwargs):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("boom")
        return original(**kwargs)

    monkeypatch.setattr(OrderItem.objects, "create", create_then_explode)

    with pytest.raises(RuntimeError):
        place_order(cart, cart.user, checkout_data)

    assert not Order.objects.exists()
    assert not OrderItem.objects.exists()
    assert CartItem.objects.count() == 2


# --- Coupons ------------------------------------------------------------------


def test_an_order_wide_coupon_discounts_the_whole_cart(
    cart, cart_item, coupon, checkout_data
):
    order = place_order(cart, cart.user, checkout_data, coupon_code=coupon.code)

    assert order.coupon_code == "FALL26"
    assert order.discount_amount == Decimal("140.00")  # 20% of 699.98, rounded
    assert order.total == Decimal("559.98")
    assert order.subtotal == Decimal("699.98")


def test_a_product_specific_coupon_discounts_only_its_line(
    cart, cart_item, category, product_coupon, checkout_data
):
    """``product_coupon`` targets ``cart_item.product``; a second, unrelated
    line in the cart must be left untouched by the discount."""
    other = Product.objects.create(
        name="Charging Pillow",
        slug="charging-pillow",
        price=Decimal("69.00"),
        category=category,
    )
    cart.add(other)

    order = place_order(cart, cart.user, checkout_data, coupon_code=product_coupon.code)

    # 15% of the Seraphine Home Hub line only (2 x 349.99 = 699.98); the
    # Charging Pillow line (69.00) is untouched.
    assert order.discount_amount == Decimal("105.00")
    assert order.subtotal == Decimal("768.98")
    assert order.total == Decimal("663.98")


def test_the_coupon_code_is_case_insensitive_and_untrimmed(
    cart, cart_item, coupon, checkout_data
):
    order = place_order(cart, cart.user, checkout_data, coupon_code=" fall26 ")

    assert order.coupon_code == "FALL26"


def test_an_unrecognized_code_is_rejected(cart, cart_item, checkout_data):
    with pytest.raises(CouponError, match="isn't recognized"):
        place_order(cart, cart.user, checkout_data, coupon_code="NOPE")

    assert not Order.objects.exists()


def test_a_retired_code_is_rejected(cart, cart_item, coupon, checkout_data):
    coupon.is_active = False
    coupon.save()

    with pytest.raises(CouponError, match="retired"):
        place_order(cart, cart.user, checkout_data, coupon_code=coupon.code)


def test_an_expired_code_is_rejected(cart, cart_item, coupon, checkout_data):
    coupon.expires_at = timezone.now() - timedelta(days=1)
    coupon.save()

    with pytest.raises(CouponError, match="expired"):
        place_order(cart, cart.user, checkout_data, coupon_code=coupon.code)


def test_a_product_coupon_is_rejected_if_that_product_is_not_in_the_cart(
    cart, cart_item, product_coupon, checkout_data
):
    """``cart_item`` is the Seraphine hub; ``product_coupon`` targets it, so
    swap the cart to hold something else entirely."""
    cart.items.all().delete()
    other = Product.objects.create(
        name="Charging Pillow",
        slug="charging-pillow",
        price=Decimal("69.00"),
        category=cart_item.product.category,
    )
    cart.add(other)

    with pytest.raises(CouponError, match="only applies to"):
        place_order(cart, cart.user, checkout_data, coupon_code=product_coupon.code)


def test_a_code_already_used_by_this_customer_is_rejected(
    cart, cart_item, coupon, checkout_data
):
    place_order(cart, cart.user, dict(checkout_data), coupon_code=coupon.code)
    cart.items.create(product=cart_item.product, quantity=1)

    with pytest.raises(CouponError, match="already used"):
        place_order(cart, cart.user, checkout_data, coupon_code=coupon.code)


def test_retiring_a_coupon_does_not_change_a_past_order(
    cart, cart_item, coupon, checkout_data
):
    order = place_order(cart, cart.user, checkout_data, coupon_code=coupon.code)
    original_discount = order.discount_amount
    original_total = order.total

    coupon.is_active = False
    coupon.save()
    coupon.delete()

    order.refresh_from_db()
    assert order.discount_amount == original_discount
    assert order.total == original_total
    assert order.coupon_code == "FALL26"


def test_a_failed_coupon_leaves_no_partial_order(cart, cart_item, checkout_data):
    with pytest.raises(CouponError):
        place_order(cart, cart.user, checkout_data, coupon_code="NOPE")

    assert not Order.objects.exists()
    assert cart.items.count() == 1  # the cart is untouched
