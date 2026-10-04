"""Project-wide pytest fixtures.

Shared test data lives here as plain fixtures — no factories. The suite
grows with the project; tests never invoke the seed command.
"""

from decimal import Decimal
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from coupons.models import Coupon
from orders.models import Cart, CartItem
from products.models import Category, Product, Tag


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Keep test uploads out of the real ``media/`` directory."""
    settings.MEDIA_ROOT = tmp_path


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
