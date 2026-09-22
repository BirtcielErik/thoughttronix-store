"""Saved addresses: the model, its manager, and owner-only access.

The view tests here concentrate on ownership. A missing
``user=request.user`` filter is the one bug in this feature with real
consequences — it would hand a customer's home address to anyone who can
guess a number in a URL.
"""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse

from .models import Address

# --- The model ---------------------------------------------------------------


def test_str_prefers_the_label(address):
    assert str(address) == "Home"


def test_str_falls_back_to_the_address_itself(address):
    address.label = ""

    assert str(address) == "12 Cortex Lane, Canyon TX"


def test_as_initial_uses_the_checkout_field_names(address):
    assert address.as_initial("shipping") == {
        "shipping_name": "Casey Monroe",
        "shipping_street": "12 Cortex Lane",
        "shipping_line2": "Unit 7",
        "shipping_city": "Canyon",
        "shipping_state": "TX",
        # The model says zip_code; the checkout form says zip.
        "shipping_zip": "79015",
    }


def test_one_address_serves_both_slots(address):
    shipping = address.as_initial("shipping")
    billing = address.as_initial("billing")

    assert shipping["shipping_street"] == billing["billing_street"]


def test_a_customer_cannot_hold_two_default_shipping_addresses(address, customer):
    address.apply_defaults(shipping=True, billing=False)

    with pytest.raises(IntegrityError), transaction.atomic():
        Address.objects.create(
            user=customer,
            name="Casey Monroe",
            street="500 Mind Street",
            city="Amarillo",
            state="TX",
            zip_code="79101",
            is_default_shipping=True,
        )


def test_two_customers_may_each_have_a_default(address, customer):
    address.apply_defaults(shipping=True, billing=False)
    other = get_user_model().objects.create_user(username="other", password="x")

    theirs = Address.objects.create(
        user=other,
        name="Robin Vale",
        street="500 Mind Street",
        city="Amarillo",
        state="TX",
        zip_code="79101",
    )
    theirs.apply_defaults(shipping=True, billing=False)

    assert Address.objects.filter(is_default_shipping=True).count() == 2


def test_apply_defaults_clears_the_address_it_displaces(address, customer):
    address.apply_defaults(shipping=True, billing=True)
    replacement = Address.objects.create(
        user=customer,
        name="Casey Monroe",
        street="500 Mind Street",
        city="Amarillo",
        state="TX",
        zip_code="79101",
    )

    replacement.apply_defaults(shipping=True, billing=False)

    address.refresh_from_db()
    assert not address.is_default_shipping
    assert address.is_default_billing  # untouched: only shipping moved
    assert replacement.is_default_shipping


def test_apply_defaults_can_stand_an_address_down(address):
    address.apply_defaults(shipping=True, billing=True)

    address.apply_defaults(shipping=False, billing=False)

    address.refresh_from_db()
    assert not address.is_default_shipping
    assert not address.is_default_billing


# --- The manager -------------------------------------------------------------


def test_remember_saves_one_slot_of_a_checkout(customer):
    checkout_data = {
        "shipping_name": "Casey Monroe",
        "shipping_street": "12 Cortex Lane",
        "shipping_line2": "Unit 7",
        "shipping_city": "Canyon",
        "shipping_state": "TX",
        "shipping_zip": "79015",
    }

    saved = Address.objects.remember(customer, checkout_data, "shipping")

    assert saved.user == customer
    assert saved.street == "12 Cortex Lane"
    assert saved.zip_code == "79015"
    assert saved.label == ""  # nothing to name it with at checkout


def test_remember_reuses_an_identical_address(address, customer):
    checkout_data = {
        f"shipping_{suffix}": value
        for suffix, value in (
            ("name", "Casey Monroe"),
            ("street", "12 Cortex Lane"),
            ("line2", "Unit 7"),
            ("city", "Canyon"),
            ("state", "TX"),
            ("zip", "79015"),
        )
    }

    again = Address.objects.remember(customer, checkout_data, "shipping")

    assert again == address
    assert Address.objects.count() == 1


# --- Owner-only access -------------------------------------------------------


def test_the_address_book_requires_login(client, db):
    response = client.get(reverse("accounts:addresses"))

    assert response.status_code == HTTPStatus.FOUND


def test_the_address_book_lists_only_your_own(client, address):
    other = get_user_model().objects.create_user(username="other", password="x")
    client.force_login(other)

    response = client.get(reverse("accounts:addresses"))

    assert "12 Cortex Lane" not in response.content.decode()


def test_an_empty_address_book_shows_its_empty_state(client, customer):
    client.force_login(customer)

    response = client.get(reverse("accounts:addresses"))

    assert "No addresses saved yet" in response.content.decode()


def test_cannot_open_another_customers_address(client, address):
    other = get_user_model().objects.create_user(username="other", password="x")
    client.force_login(other)

    response = client.get(reverse("accounts:address_update", kwargs={"pk": address.pk}))

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_cannot_delete_another_customers_address(client, address):
    other = get_user_model().objects.create_user(username="other", password="x")
    client.force_login(other)

    response = client.post(
        reverse("accounts:address_delete", kwargs={"pk": address.pk})
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert Address.objects.filter(pk=address.pk).exists()


# --- Creating, editing and deleting ------------------------------------------


def test_creating_an_address_files_it_under_the_signed_in_customer(client, customer):
    client.force_login(customer)

    client.post(
        reverse("accounts:address_create"),
        {
            "label": "Work",
            "name": "Casey Monroe",
            "street": "500 Mind Street",
            "line2": "",
            "city": "Amarillo",
            "state": "TX",
            "zip_code": "79101",
            "is_default_shipping": "on",
        },
    )

    saved = Address.objects.get()
    assert saved.user == customer
    assert saved.is_default_shipping
    assert not saved.is_default_billing


def test_making_an_address_default_stands_the_previous_one_down(
    client, address, customer
):
    address.apply_defaults(shipping=True, billing=False)
    client.force_login(customer)

    client.post(
        reverse("accounts:address_create"),
        {
            "label": "Work",
            "name": "Casey Monroe",
            "street": "500 Mind Street",
            "line2": "",
            "city": "Amarillo",
            "state": "TX",
            "zip_code": "79101",
            "is_default_shipping": "on",
        },
    )

    address.refresh_from_db()
    assert not address.is_default_shipping
    assert Address.objects.filter(is_default_shipping=True).count() == 1


def test_deleting_removes_the_address(client, address, customer):
    client.force_login(customer)

    client.post(reverse("accounts:address_delete", kwargs={"pk": address.pk}))

    assert not Address.objects.exists()
