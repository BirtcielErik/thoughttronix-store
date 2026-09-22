"""Order model behavior, the checkout flow, and owner-only access."""

import datetime
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from .models import CartItem, Order
from .services import place_order
from .test_checkout_form import VALID_DATA


@pytest.fixture
def order(cart, cart_item):
    return place_order(cart, cart.user, dict(VALID_DATA))


@pytest.fixture
def other_customer(db):
    return get_user_model().objects.create_user(username="other", password="x")


# --- Model behavior ----------------------------------------------------------


def test_order_number_format(order):
    assert order.number == f"TT-{order.created_at.year}-{order.pk:05d}"
    assert str(order) == order.number


def test_orders_come_most_recent_first(customer, order):
    older = Order.objects.create(
        user=customer,
        total=Decimal("9.00"),
        email="casey@example.com",
        shipping_name="Casey Monroe",
        shipping_street="12 Cortex Lane",
        shipping_city="Canyon",
        shipping_state="TX",
        shipping_zip="79015",
        billing_name="Casey Monroe",
        billing_street="12 Cortex Lane",
        billing_city="Canyon",
        billing_state="TX",
        billing_zip="79015",
        card_last4="4242",
        created_at=timezone.now() - datetime.timedelta(days=30),
    )

    assert list(Order.objects.all()) == [order, older]


def test_order_item_str(order):
    assert str(order.items.get()) == "2 × Seraphine Home Hub"


# --- The checkout page -------------------------------------------------------


def test_checkout_requires_login(client, db):
    response = client.get(reverse("orders:checkout"))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


def test_an_empty_cart_is_sent_back_to_the_cart_page(client, customer):
    client.force_login(customer)

    response = client.get(reverse("orders:checkout"))

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("orders:cart")


def test_an_unavailable_line_is_sent_back_to_the_cart_page(
    client, customer, cart, cart_item, unavailable_product
):
    cart.items.create(product=unavailable_product)
    client.force_login(customer)

    response = client.get(reverse("orders:checkout"))

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("orders:cart")


def test_checkout_page_shows_the_form_and_the_cart(client, customer, cart_item):
    client.force_login(customer)

    response = client.get(reverse("orders:checkout"))

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "Shipping address" in page
    assert "Billing address" in page
    assert "Seraphine Home Hub" in page
    assert "699.98" in page


def test_a_valid_checkout_places_the_order(client, customer, cart_item):
    client.force_login(customer)

    response = client.post(reverse("orders:checkout"), VALID_DATA)

    order = Order.objects.get()
    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("orders:confirmation", kwargs={"pk": order.pk})
    assert not CartItem.objects.exists()


def test_an_invalid_checkout_preserves_input_and_places_nothing(
    client, customer, cart_item
):
    bad = {**VALID_DATA, "card_number": "4242 4242 4242 4241"}
    client.force_login(customer)

    response = client.post(reverse("orders:checkout"), bad)

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "Enter a valid card number." in page
    assert "12 Cortex Lane" in page  # everything typed is preserved
    assert not Order.objects.exists()
    assert CartItem.objects.exists()


# --- The saved-address picker (HTMX) -----------------------------------------


def test_checkout_offers_the_customers_saved_addresses(
    client, customer, cart_item, address
):
    client.force_login(customer)

    response = client.get(reverse("orders:checkout"))

    page = response.content.decode()
    assert "Use a saved address" in page
    assert reverse("orders:checkout_address", kwargs={"slot": "shipping"}) in page
    assert f'<option value="{address.pk}">Home</option>' in page


def test_checkout_hides_the_picker_when_nothing_is_saved(client, customer, cart_item):
    client.force_login(customer)

    response = client.get(reverse("orders:checkout"))

    assert "Use a saved address" not in response.content.decode()


def test_checkout_prefills_from_the_default_addresses(
    client, customer, cart_item, address
):
    address.apply_defaults(shipping=True, billing=False)
    client.force_login(customer)

    response = client.get(reverse("orders:checkout"))

    initial = response.context["form"].initial
    assert initial["shipping_street"] == "12 Cortex Lane"
    assert "billing_street" not in initial  # no default billing address set


def test_the_picker_returns_the_slot_fields_filled_in(client, customer, address):
    client.force_login(customer)

    response = client.get(
        reverse("orders:checkout_address", kwargs={"slot": "billing"}),
        {"saved_address": address.pk},
    )

    page = response.content.decode()
    assert response.status_code == HTTPStatus.OK
    assert 'id="billing-fields"' in page
    assert 'name="billing_street"' in page
    assert "12 Cortex Lane" in page
    # Only the one section comes back — nothing else on the page is disturbed.
    assert 'name="shipping_street"' not in page
    assert 'name="card_number"' not in page


def test_the_picker_rejects_an_unknown_slot(client, customer, address):
    client.force_login(customer)

    response = client.get(
        reverse("orders:checkout_address", kwargs={"slot": "banana"}),
        {"saved_address": address.pk},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize("chosen", ["", "banana", None])
def test_the_picker_rejects_a_missing_or_malformed_choice(client, customer, chosen):
    """A blank or non-numeric pk must 404, not raise ValueError as a 500."""
    client.force_login(customer)

    response = client.get(
        reverse("orders:checkout_address", kwargs={"slot": "shipping"}),
        {} if chosen is None else {"saved_address": chosen},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_the_picker_cannot_reach_another_customers_address(
    client, other_customer, address
):
    client.force_login(other_customer)

    response = client.get(
        reverse("orders:checkout_address", kwargs={"slot": "shipping"}),
        {"saved_address": address.pk},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_confirmation_shows_the_order_number(client, customer, order):
    client.force_login(customer)

    response = client.get(reverse("orders:confirmation", kwargs={"pk": order.pk}))

    assert response.status_code == HTTPStatus.OK
    assert order.number in response.content.decode()


# --- Order history and detail ------------------------------------------------


def test_history_requires_login(client, db):
    response = client.get(reverse("orders:history"))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


def test_history_lists_the_customers_orders(client, customer, order):
    client.force_login(customer)

    response = client.get(reverse("orders:history"))

    assert response.status_code == HTTPStatus.OK
    assert order.number in response.content.decode()


def test_history_has_a_designed_empty_state(client, customer):
    client.force_login(customer)

    response = client.get(reverse("orders:history"))

    assert "No orders yet" in response.content.decode()


def test_detail_shows_purchase_time_prices(client, customer, order):
    order.items.get().product.__class__.objects.update(price=Decimal("999.00"))
    client.force_login(customer)

    response = client.get(reverse("orders:detail", kwargs={"pk": order.pk}))

    page = response.content.decode()
    assert "349.99" in page
    assert "card ending 4242" in page
    assert "12 Cortex Lane" in page


def test_customers_cannot_see_anothers_orders(client, other_customer, order):
    client.force_login(other_customer)

    assert (
        client.get(reverse("orders:detail", kwargs={"pk": order.pk})).status_code
        == HTTPStatus.NOT_FOUND
    )
    assert (
        client.get(reverse("orders:confirmation", kwargs={"pk": order.pk})).status_code
        == HTTPStatus.NOT_FOUND
    )
    history = client.get(reverse("orders:history"))
    assert order.number not in history.content.decode()
