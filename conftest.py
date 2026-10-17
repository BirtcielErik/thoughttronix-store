"""Project-wide pytest fixtures.

Shared test data lives here as plain fixtures — no factories. The suite
grows with the project; tests never invoke the seed command.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from accounts.models import Address
from coupons.models import Coupon
from orders.models import Cart, CartItem
from products.models import Category, Product, Tag
from wishlist.models import Wishlist


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Every test writes media to a throwaway folder, never the real media/.

    ``seed`` wipes ``MEDIA_ROOT/products``, and the real folder holds
    committed uploads that a test run must not delete.
    """
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


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
def superuser(db):
    return get_user_model().objects.create_superuser(
        username="admin", email="admin@example.com", password="admin123"
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
def address(customer):
    """A saved address matching the shipping half of the checkout test data."""
    return Address.objects.create(
        user=customer,
        label="Home",
        name="Casey Monroe",
        street="12 Cortex Lane",
        line2="Unit 7",
        city="Canyon",
        state="TX",
        zip_code="79015",
    )


@pytest.fixture
def cart(customer):
    return Cart.for_user(customer)


@pytest.fixture
def cart_item(cart, product):
    return CartItem.objects.create(cart=cart, product=product, quantity=2)


@pytest.fixture
def wishlist(customer):
    return Wishlist.for_user(customer)


@pytest.fixture
def order_coupon(db):
    """15% off the whole order, no dates, no minimum."""
    return Coupon.objects.create(
        code="THOUGHTS15", kind=Coupon.Kind.PERCENT, value=Decimal("15")
    )


@pytest.fixture
def item_coupon(product):
    """$25 off the Seraphine Home Hub line."""
    return Coupon.objects.create(
        code="SERAPHINE25",
        kind=Coupon.Kind.AMOUNT,
        value=Decimal("25.00"),
        product=product,
    )
