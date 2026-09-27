"""place_order tests — coverage priority 3 in the PRD.

Denormalization, cart emptying, atomicity, unavailable rejection, the
card_last4-only rule, and applying a coupon. The coupon's own rules
(dates, minimum spend, once per customer) are tested in ``coupons``.
"""

import datetime
from decimal import Decimal

import pytest

from accounts.models import Address
from coupons.models import CouponError
from products.models import Product

from .models import CartItem, Order, OrderItem
from .services import place_order
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


def test_no_coupon_means_no_discount(cart, cart_item, checkout_data):
    order = place_order(cart, cart.user, checkout_data)

    assert order.discount == Decimal("0.00")
    assert order.coupon is None
    assert order.coupon_code == ""
    assert order.subtotal == order.total


def test_an_order_coupon_discounts_the_total(
    cart, cart_item, order_coupon, checkout_data
):
    order = place_order(cart, cart.user, checkout_data, coupon_code="thoughts15 ")

    # 15% of 699.98 = 104.997, rounded half-up to the cent.
    assert order.discount == Decimal("105.00")
    assert order.total == Decimal("594.98")
    assert order.subtotal == Decimal("699.98")
    assert order.coupon == order_coupon
    assert order.coupon_code == "THOUGHTS15"
    assert order.items.get().discount == Decimal("0.00")  # not spread to lines


def test_an_item_coupon_lands_on_its_line(
    cart, cart_item, item_coupon, category, checkout_data
):
    other = Product.objects.create(
        name="Charging Pillow",
        slug="charging-pillow",
        price=Decimal("69.00"),
        category=category,
    )
    cart.add(other)

    order = place_order(cart, cart.user, checkout_data, coupon_code="SERAPHINE25")

    assert order.discount == Decimal("50.00")  # $25 × 2 Hubs
    assert order.total == Decimal("718.98")  # 699.98 + 69.00 - 50.00
    hub = order.items.get(product_name="Seraphine Home Hub")
    assert hub.discount == Decimal("50.00")
    assert hub.charged_total == Decimal("649.98")
    assert order.items.get(product_name="Charging Pillow").discount == 0


def test_the_discount_is_a_snapshot(cart, cart_item, order_coupon, checkout_data):
    order = place_order(cart, cart.user, checkout_data, coupon_code="THOUGHTS15")

    order_coupon.is_active = False
    order_coupon.ends_on = datetime.date(2020, 1, 1)
    order_coupon.save()

    order.refresh_from_db()
    assert order.discount == Decimal("105.00")
    assert order.coupon_code == "THOUGHTS15"


def test_a_bad_coupon_places_nothing(cart, cart_item, order_coupon, checkout_data):
    order_coupon.is_active = False
    order_coupon.save()

    with pytest.raises(CouponError, match="no longer valid"):
        place_order(cart, cart.user, checkout_data, coupon_code="THOUGHTS15")

    assert not Order.objects.exists()
    assert cart.items.count() == 1  # the cart is untouched


def test_a_coupon_error_is_a_value_error(cart, cart_item, checkout_data):
    """place_order's documented contract: failures raise ValueError."""
    with pytest.raises(ValueError, match="don't recognize"):
        place_order(cart, cart.user, checkout_data, coupon_code="NOPE")


def test_a_blank_coupon_code_is_no_coupon(cart, cart_item, checkout_data):
    order = place_order(cart, cart.user, checkout_data, coupon_code="  ")

    assert order.coupon is None


# --- Saving addresses to the account -----------------------------------------


def test_nothing_is_saved_unless_the_customer_asks(cart, cart_item, checkout_data):
    place_order(cart, cart.user, checkout_data)

    assert not Address.objects.exists()


def test_a_ticked_box_saves_that_slot(cart, cart_item, checkout_data):
    checkout_data["save_shipping_address"] = True

    place_order(cart, cart.user, checkout_data)

    saved = Address.objects.get()
    assert saved.user == cart.user
    assert saved.street == "12 Cortex Lane"
    assert saved.zip_code == "79015"


def test_both_slots_can_be_saved_at_once(cart, cart_item, checkout_data):
    checkout_data["save_shipping_address"] = True
    checkout_data["save_billing_address"] = True

    place_order(cart, cart.user, checkout_data)

    # Same street, different ZIP in the test data — two distinct addresses.
    assert Address.objects.count() == 2


def test_saving_an_address_already_on_file_does_not_duplicate_it(
    cart, cart_item, checkout_data, address
):
    checkout_data["save_shipping_address"] = True

    place_order(cart, cart.user, checkout_data)

    assert Address.objects.count() == 1


def test_deleting_a_saved_address_leaves_the_order_untouched(
    cart, cart_item, checkout_data
):
    """The payoff of the snapshot design: no FK from Order to Address."""
    checkout_data["save_shipping_address"] = True
    order = place_order(cart, cart.user, checkout_data)

    Address.objects.get().delete()

    order.refresh_from_db()
    assert order.shipping_street == "12 Cortex Lane"
