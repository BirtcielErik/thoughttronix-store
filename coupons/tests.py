"""Coupons: the model's rules, the back-office form, and the staff screens.

Applying a coupon to a real order is tested beside ``place_order`` in
``orders/test_services.py``; the checkout preview in ``orders/tests.py``.
"""

import datetime
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.urls import reverse
from django.utils import timezone

from orders.models import Cart, Order
from orders.services import place_order
from orders.test_checkout_form import VALID_DATA
from products.models import Product

from .forms import CouponForm
from .models import Coupon, CouponError

TODAY = timezone.localdate


def days(n):
    return TODAY() + datetime.timedelta(days=n)


def use(coupon, cart, product):
    """Place an order with ``coupon``, then refill the cart for the next test step."""
    order = place_order(cart, cart.user, dict(VALID_DATA), coupon_code=coupon.code)
    cart.items.create(product=product, quantity=2)
    return order


# --- Codes ----------------------------------------------------------------------


def test_codes_are_stored_uppercase(db):
    coupon = Coupon.objects.create(code=" fall15 ", value=Decimal("15"))

    assert coupon.code == "FALL15"


def test_lookup_ignores_case_and_spaces(order_coupon):
    assert Coupon.objects.lookup("  thoughts15 ") == order_coupon


def test_an_unknown_code_is_a_coupon_error(db):
    with pytest.raises(CouponError, match="don't recognize"):
        Coupon.objects.lookup("NOPE")


# --- Status -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("is_active", "starts", "ends", "status"),
    [
        (True, None, None, Coupon.Status.ACTIVE),
        (True, 0, 0, Coupon.Status.ACTIVE),  # the window is inclusive
        (True, 1, None, Coupon.Status.SCHEDULED),
        (True, None, -1, Coupon.Status.EXPIRED),
        (False, None, None, Coupon.Status.RETIRED),
        (False, None, -1, Coupon.Status.RETIRED),  # retired wins
    ],
)
def test_status_follows_the_switch_and_the_dates(
    order_coupon, is_active, starts, ends, status
):
    order_coupon.is_active = is_active
    order_coupon.starts_on = days(starts) if starts is not None else None
    order_coupon.ends_on = days(ends) if ends is not None else None

    assert order_coupon.status == status


# --- The math -------------------------------------------------------------------


def test_percent_rounds_half_up_to_the_cent(order_coupon):
    # 15% of 0.10 = 0.015 → 0.02
    assert order_coupon.amount_off(Decimal("0.10")) == Decimal("0.02")


def test_a_fixed_amount_is_capped_at_the_base(item_coupon):
    assert item_coupon.amount_off(Decimal("100.00")) == Decimal("25.00")
    assert item_coupon.amount_off(Decimal("6.00")) == Decimal("6.00")


def test_a_fixed_amount_comes_off_each_unit(item_coupon):
    assert item_coupon.amount_off(Decimal("300.00"), units=3) == Decimal("75.00")


def test_a_fixed_amount_per_unit_is_capped_at_the_base(item_coupon):
    # 3 × $25 = $75, but three $20 units only total $60.
    assert item_coupon.amount_off(Decimal("60.00"), units=3) == Decimal("60.00")


def test_a_percentage_ignores_units(order_coupon):
    assert order_coupon.amount_off(Decimal("100.00"), units=3) == Decimal("15.00")


def test_summary_reads_as_an_offer(order_coupon, item_coupon):
    assert order_coupon.summary == "15% off the whole order"
    assert item_coupon.summary == "$25.00 off each Seraphine Home Hub"


# --- discount_for: every way a code can fail -------------------------------------


def test_an_order_coupon_discounts_the_subtotal(cart, cart_item, order_coupon):
    discount = order_coupon.discount_for(cart, cart.user)

    assert discount.amount == Decimal("105.00")  # 15% of 699.98
    assert discount.product is None


def test_an_item_coupon_discounts_each_unit_on_its_line(cart, cart_item, item_coupon):
    discount = item_coupon.discount_for(cart, cart.user)

    assert discount.amount == Decimal("50.00")  # $25 × 2 Hubs
    assert discount.product == cart_item.product


def test_an_item_coupon_on_one_unit_takes_its_amount_once(cart, cart_item, item_coupon):
    cart_item.quantity = 1
    cart_item.save()

    assert item_coupon.discount_for(cart, cart.user).amount == Decimal("25.00")


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"is_active": False}, "no longer valid"),
        ({"starts_on": 1}, "isn't valid until"),
        ({"ends_on": -1}, "expired on"),
        ({"min_spend": Decimal("700.00")}, r"at least \$700.00"),
    ],
)
def test_a_code_is_refused_with_a_reason(
    cart, cart_item, order_coupon, change, message
):
    for name, value in change.items():
        if name.endswith("_on"):
            value = days(value)
        setattr(order_coupon, name, value)

    with pytest.raises(CouponError, match=message):
        order_coupon.discount_for(cart, cart.user)


def test_minimum_spend_is_measured_against_the_cart_subtotal(
    cart, cart_item, item_coupon
):
    # The Hub line alone is 699.98; the minimum counts the whole cart.
    item_coupon.min_spend = Decimal("699.98")

    assert item_coupon.discount_for(cart, cart.user).amount == Decimal("50.00")


def test_an_item_coupon_needs_its_product_in_the_cart(cart, item_coupon, category):
    cart.add(
        Product.objects.create(
            name="Charging Pillow",
            slug="charging-pillow",
            price=Decimal("69.00"),
            category=category,
        )
    )

    with pytest.raises(
        CouponError, match="Seraphine Home Hub, which isn't in your cart"
    ):
        item_coupon.discount_for(cart, cart.user)


def test_a_customer_can_use_a_code_once(cart, cart_item, order_coupon, product):
    use(order_coupon, cart, product)

    with pytest.raises(CouponError, match="already used"):
        order_coupon.discount_for(cart, cart.user)


def test_a_cancelled_order_gives_the_use_back(cart, cart_item, order_coupon, product):
    order = use(order_coupon, cart, product)
    order.status = Order.Status.CANCELLED
    order.save()

    assert order_coupon.discount_for(cart, cart.user).amount > 0


def test_another_customer_can_still_use_the_code(
    cart, cart_item, order_coupon, product, staff_user
):
    use(order_coupon, cart, product)

    assert order_coupon.discount_for(cart, staff_user).amount > 0


# --- Model validation --------------------------------------------------------------


def test_a_percentage_over_100_is_refused(db):
    coupon = Coupon(code="TOOMUCH", kind=Coupon.Kind.PERCENT, value=Decimal("101"))

    with pytest.raises(ValidationError) as error:
        coupon.full_clean()

    assert "value" in error.value.message_dict


def test_the_window_must_be_in_order(db):
    coupon = Coupon(
        code="BACKWARDS", value=Decimal("10"), starts_on=days(5), ends_on=days(1)
    )

    with pytest.raises(ValidationError) as error:
        coupon.full_clean()

    assert "ends_on" in error.value.message_dict


def test_codes_are_unique_regardless_of_case(order_coupon):
    with pytest.raises(ValidationError) as error:
        Coupon(code="thoughts15", value=Decimal("5")).full_clean()

    assert "code" in error.value.message_dict


def test_a_used_coupon_locks_its_terms_but_not_its_schedule(
    cart, cart_item, order_coupon, product
):
    use(order_coupon, cart, product)

    order_coupon.ends_on = days(30)
    order_coupon.is_active = False
    order_coupon.full_clean()  # the schedule is still editable

    order_coupon.value = Decimal("30")
    with pytest.raises(ValidationError, match="terms are locked"):
        order_coupon.full_clean()


def test_a_used_coupon_cannot_be_deleted(cart, cart_item, order_coupon, product):
    use(order_coupon, cart, product)

    with pytest.raises(ProtectedError):
        order_coupon.delete()


# --- Usage --------------------------------------------------------------------------


def test_usage_counts_non_cancelled_orders(
    cart, cart_item, order_coupon, item_coupon, product, staff_user
):
    use(order_coupon, cart, product)
    other_cart = Cart.for_user(staff_user)
    other_cart.items.create(product=product, quantity=2)
    cancelled = use(order_coupon, other_cart, product)
    cancelled.status = Order.Status.CANCELLED
    cancelled.save()

    usage = {coupon.code: coupon for coupon in Coupon.objects.with_usage()}

    assert usage["THOUGHTS15"].uses == 1
    assert usage["THOUGHTS15"].discounted == Decimal("105.00")
    assert usage["SERAPHINE25"].uses == 0
    assert usage["SERAPHINE25"].discounted == Decimal("0.00")


# --- The back-office form -------------------------------------------------------------


def test_the_form_locks_terms_once_used(cart, cart_item, order_coupon, product):
    assert not CouponForm(instance=order_coupon).terms_locked

    use(order_coupon, cart, product)
    form = CouponForm(instance=order_coupon)

    assert form.terms_locked
    assert all(form.fields[name].disabled for name in Coupon.TERMS)
    assert not form.fields["ends_on"].disabled


def test_posting_changed_terms_to_a_used_coupon_changes_nothing(
    cart, cart_item, order_coupon, product
):
    use(order_coupon, cart, product)
    form = CouponForm(
        data={"code": "FREE", "kind": "PERCENT", "value": "99", "is_active": "on"},
        instance=order_coupon,
    )

    assert form.is_valid(), form.errors
    form.save()
    order_coupon.refresh_from_db()
    assert (order_coupon.code, order_coupon.value) == ("THOUGHTS15", Decimal("15.00"))


# --- The staff screens -------------------------------------------------------------------

STAFF_URLS = [
    ("coupons:manage_coupons", False),
    ("coupons:manage_coupon_create", False),
    ("coupons:manage_coupon_detail", True),
    ("coupons:manage_coupon_update", True),
]


@pytest.mark.parametrize(("name", "needs_pk"), STAFF_URLS)
def test_customers_cannot_reach_the_coupon_screens(
    client, customer, order_coupon, name, needs_pk
):
    client.force_login(customer)
    url = reverse(name, kwargs={"pk": order_coupon.pk} if needs_pk else None)

    assert client.get(url).status_code == HTTPStatus.FORBIDDEN


@pytest.mark.parametrize(("name", "needs_pk"), STAFF_URLS)
def test_staff_can_reach_the_coupon_screens(
    client, staff_user, order_coupon, name, needs_pk
):
    client.force_login(staff_user)
    url = reverse(name, kwargs={"pk": order_coupon.pk} if needs_pk else None)

    assert client.get(url).status_code == HTTPStatus.OK


def test_the_list_is_in_code_order(client, staff_user, order_coupon, item_coupon):
    client.force_login(staff_user)

    response = client.get(reverse("coupons:manage_coupons"))

    codes = [coupon.code for coupon in response.context["coupons"]]
    assert codes == ["SERAPHINE25", "THOUGHTS15"]


def test_the_list_shows_an_empty_state(client, staff_user):
    client.force_login(staff_user)

    response = client.get(reverse("coupons:manage_coupons"))

    assert b"No coupons yet" in response.content


def test_staff_can_create_a_coupon(client, staff_user, product):
    client.force_login(staff_user)

    response = client.post(
        reverse("coupons:manage_coupon_create"),
        {
            "code": "hub-deal",
            "kind": "AMOUNT",
            "value": "40.00",
            "product": product.pk,
            "starts_on": str(days(0)),
            "ends_on": str(days(30)),
            "is_active": "on",
        },
    )

    coupon = Coupon.objects.get()
    assert response.status_code == HTTPStatus.FOUND
    assert coupon.code == "HUB-DEAL"
    assert coupon.product == product
    assert coupon.status == Coupon.Status.ACTIVE


def test_staff_can_retire_and_reactivate_a_coupon(client, staff_user, order_coupon):
    client.force_login(staff_user)
    url = reverse("coupons:manage_coupon_toggle", kwargs={"pk": order_coupon.pk})

    client.post(url)
    order_coupon.refresh_from_db()
    assert order_coupon.status == Coupon.Status.RETIRED

    client.post(url)
    order_coupon.refresh_from_db()
    assert order_coupon.status == Coupon.Status.ACTIVE


def test_the_toggle_is_post_only(client, staff_user, order_coupon):
    client.force_login(staff_user)
    url = reverse("coupons:manage_coupon_toggle", kwargs={"pk": order_coupon.pk})

    assert client.get(url).status_code == HTTPStatus.METHOD_NOT_ALLOWED


def test_a_product_a_coupon_targets_cannot_be_deleted(client, staff_user, item_coupon):
    client.force_login(staff_user)
    product = item_coupon.product

    response = client.post(
        reverse("products:manage_product_delete", kwargs={"pk": product.pk}),
        follow=True,
    )

    assert Product.objects.filter(pk=product.pk).exists()
    assert b"SERAPHINE25 targets it" in response.content
