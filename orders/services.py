"""Order placement — one of the codebase's two deliberate deep modules.

The interface is the product: one function that turns a cart and a
validated checkout into an order, all-or-nothing. Callers never touch
``Order`` construction directly.
"""

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from coupons.models import Coupon

from .models import Cart, Order, OrderItem

ADDRESS_FIELDS = [
    "email",
    "shipping_name",
    "shipping_street",
    "shipping_line2",
    "shipping_city",
    "shipping_state",
    "shipping_zip",
    "billing_name",
    "billing_street",
    "billing_line2",
    "billing_city",
    "billing_state",
    "billing_zip",
]


class CouponError(ValueError):
    """An invalid coupon code; the message is safe to show the customer."""


def resolve_coupon(code: str, *, user: AbstractBaseUser, cart: Cart) -> Coupon:
    """Validate a coupon code against this user's cart and return it.

    The one place every coupon rule lives, reused by the cart's apply
    action, the checkout page's pre-check, and ``place_order``'s backstop.
    Raises ``CouponError`` — never a bare exception — for a code that's
    unrecognized, retired, expired, doesn't apply to anything in the cart,
    or has already been used by this customer.
    """
    try:
        coupon = Coupon.objects.get(code=code.strip().upper())
    except Coupon.DoesNotExist:
        raise CouponError("That code isn't recognized.") from None
    if not coupon.is_active:
        raise CouponError("That code has been retired.")
    if coupon.is_expired():
        raise CouponError("Oops! That discount code is expired or has reached its usage limit.")
    if coupon.product_id and not any(
        line.product_id == coupon.product_id for line in cart.lines()
    ):
        raise CouponError(f"{coupon.code} only applies to {coupon.product.name}.")
    if Order.objects.filter(user=user, coupon_code=coupon.code).exists():
        raise CouponError("You've already used that code.")
    return coupon


def compute_discount(cart: Cart, coupon: Coupon | None) -> Decimal:
    """The dollar amount ``coupon`` knocks off this cart.

    Order-wide coupons (no ``product``) discount the whole cart; a
    product-specific coupon discounts only the matching line(s).
    """
    if coupon is None:
        return Decimal("0.00")
    if coupon.product_id:
        base = sum(
            (
                line.line_total
                for line in cart.lines()
                if line.product_id == coupon.product_id
            ),
            Decimal("0.00"),
        )
    else:
        base = cart.total()
    return (base * coupon.percent_off / Decimal("100")).quantize(Decimal("0.01"))


def cart_coupon(cart: Cart) -> Coupon | None:
    """The coupon a cart's stored code currently names, without re-validating it.

    For display only (cart/checkout previews) — ``resolve_coupon`` is the
    function that actually enforces usability.
    """
    if not cart.coupon_code:
        return None
    return Coupon.objects.filter(code=cart.coupon_code).first()


@transaction.atomic
def place_order(
    cart: Cart,
    user: AbstractBaseUser,
    checkout_data: Mapping[str, Any],
    *,
    coupon_code: str | None = None,
) -> Order:
    """Create an order from the cart's contents, then empty the cart.

    ``checkout_data`` is the ``cleaned_data`` of a valid ``CheckoutForm``.
    Addresses and line prices are denormalized onto the order — an order
    is a snapshot, immune to later catalog or address edits. Of the card,
    only the last four digits are stored; the full number and CVV never
    touch the database.

    All-or-nothing: runs in a transaction, so a failure partway through
    leaves no partial order and the cart intact.

    Raises ``ValueError`` if the cart is empty or holds a product that is
    no longer available. Raises ``CouponError`` (a ``ValueError``) if
    ``coupon_code`` doesn't resolve — the backstop behind the cart's apply
    action and the checkout page's own pre-check.
    """
    lines = list(cart.lines())
    if not lines:
        raise ValueError("Cannot place an order from an empty cart.")
    unavailable = [line.product.name for line in lines if not line.product.is_available]
    if unavailable:
        raise ValueError(
            f"No longer available: {', '.join(unavailable)}. "
            "Remove them from the cart to check out."
        )

    coupon = resolve_coupon(coupon_code, user=user, cart=cart) if coupon_code else None
    discount = compute_discount(cart, coupon)

    card_digits = checkout_data["card_number"].replace(" ", "").replace("-", "")
    order = Order.objects.create(
        user=user,
        total=cart.total() - discount,
        coupon_code=coupon.code if coupon else "",
        discount_amount=discount,
        card_last4=card_digits[-4:],
        **{name: checkout_data[name] for name in ADDRESS_FIELDS},
    )
    for line in lines:
        OrderItem.objects.create(
            order=order,
            product=line.product,
            product_name=line.product.name,
            unit_price=line.product.price,
            quantity=line.quantity,
        )
    cart.items.all().delete()
    cart.coupon_code = ""
    cart.save(update_fields=["coupon_code"])
    return order
