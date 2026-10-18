"""Project-wide pytest fixtures.

Shared test data lives here as plain fixtures — no factories. The suite
grows with the project; tests never invoke the seed command.
"""

from decimal import Decimal
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from coupons.models import Coupon
from orders.models import Cart, CartItem, Order, OrderItem
from products.models import Category, Product, Tag
from reviews.models import Review


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Keep test uploads out of the real ``media/`` directory."""
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture(autouse=True)
def clear_cache():
    """Start every test with empty throttle counters."""
    cache.clear()


def png_bytes():
    """A real 1x1 PNG, built in memory."""
    buffer = BytesIO()
    Image.new("RGB", (1, 1)).save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture
def png_upload():
    return SimpleUploadedFile("photo.png", png_bytes(), content_type="image/png")


@pytest.fixture
def customer(db):
    return get_user_model().objects.create_user(
        username="customer", password="customer123"
    )


@pytest.fixture
def staff_user(db):
    return get_user_model().objects.create_user(
        username="employee",
        password="employee123",
        is_staff=True,
        job_title="Junior Thought Curator",
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="Home Assistants", slug="home-assistants")


@pytest.fixture
def product(category):
    return Product.objects.create(
        name="Seraphine Home Hub",
        slug="seraphine-home-hub",
        tagline="She's always listening. In a good way.",
        description="The flagship Seraphine hub with a seven-microphone array.",
        price=Decimal("349.99"),
        category=category,
    )


@pytest.fixture
def product_with_image(product, png_upload):
    product.image = png_upload
    product.save()
    return product


@pytest.fixture
def unavailable_product(category):
    return Product.objects.create(
        name="EchoPatch",
        slug="echopatch",
        tagline="Never miss a word. Anyone's.",
        price=Decimal("139.00"),
        is_available=False,
        category=category,
    )


@pytest.fixture
def tag(db):
    return Tag.objects.create(name="bestseller", slug="bestseller")


@pytest.fixture
def cart(customer):
    return Cart.for_user(customer)


@pytest.fixture
def cart_item(cart, product):
    return CartItem.objects.create(cart=cart, product=product, quantity=2)


@pytest.fixture
def coupon(db):
    """An order-wide, active coupon."""
    return Coupon.objects.create(code="FALL26", percent_off=20)


@pytest.fixture
def product_coupon(product):
    """A coupon tied to the ``product`` fixture."""
    return Coupon.objects.create(code="SERAPHINE15", percent_off=15, product=product)


def make_order(user, product, status=Order.Status.PLACED):
    """An order of one ``product`` for ``user``, built directly at ``status``."""
    order = Order.objects.create(
        user=user,
        status=status,
        total=product.price,
        email=f"{user.username}@example.com",
        shipping_name="Ada Lovelace",
        shipping_street="1 Analytical Way",
        shipping_city="Canyon",
        shipping_state="TX",
        shipping_zip="79015",
        billing_name="Ada Lovelace",
        billing_street="1 Analytical Way",
        billing_city="Canyon",
        billing_state="TX",
        billing_zip="79015",
        card_last4="4242",
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        unit_price=product.price,
        quantity=1,
    )
    return order


@pytest.fixture
def delivered_order(customer, product):
    """The ``customer``'s delivered order of ``product`` — review-eligible."""
    return make_order(customer, product, Order.Status.DELIVERED)


@pytest.fixture
def review(delivered_order, customer, product):
    """The ``customer``'s visible review of ``product``."""
    return Review.objects.create(
        user=customer,
        product=product,
        rating=4,
        comment="Knew what I wanted before I did. Mostly delightful.",
    )
