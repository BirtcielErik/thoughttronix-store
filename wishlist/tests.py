from http import HTTPStatus

import pytest
from django.db import IntegrityError
from django.urls import reverse

from .models import Wishlist, WishlistItem

# --- Model behavior ---------------------------------------------------------


def test_wishlist_str(wishlist):
    assert str(wishlist) == "Wishlist for customer"


def test_for_user_creates_the_wishlist_once(customer):
    first = Wishlist.for_user(customer)
    second = Wishlist.for_user(customer)

    assert first == second
    assert Wishlist.objects.count() == 1


def test_add_saves_a_product(wishlist, product):
    item = wishlist.add(product)

    assert item.product == product
    assert list(wishlist.items.all()) == [item]


def test_saving_twice_leaves_a_single_item(wishlist, product):
    first = wishlist.add(product)
    second = wishlist.add(product)

    assert first == second
    assert wishlist.items.count() == 1


def test_an_unavailable_product_can_be_saved(wishlist, unavailable_product):
    wishlist.add(unavailable_product)

    assert wishlist.items.filter(product=unavailable_product).exists()


def test_remove_unsaves_a_product(wishlist, product):
    wishlist.add(product)

    wishlist.remove(product)

    assert not wishlist.items.exists()


def test_removing_an_unsaved_product_is_a_no_op(wishlist, product, category):
    wishlist.add(product)
    other = category.products.create(name="Other", slug="other", price=1)

    wishlist.remove(other)

    assert list(wishlist.items.values_list("product", flat=True)) == [product.pk]


def test_wishlist_product_pair_is_unique(wishlist, product):
    wishlist.add(product)

    with pytest.raises(IntegrityError):
        WishlistItem.objects.create(wishlist=wishlist, product=product)


# --- The button on the product page ------------------------------------------


def detail_page(client, product):
    return client.get(product.get_absolute_url()).content.decode()


def test_signed_out_button_links_to_sign_in_and_back(client, product):
    page = detail_page(client, product)

    login = reverse("accounts:login")
    assert f'href="{login}?next=/products/seraphine-home-hub/"' in page
    assert "Add to wishlist" in page
    assert reverse("wishlist:add", kwargs={"pk": product.pk}) not in page


def test_not_saved_button_posts_to_add(client, customer, product):
    client.force_login(customer)

    page = detail_page(client, product)

    assert reverse("wishlist:add", kwargs={"pk": product.pk}) in page
    assert 'aria-pressed="false"' in page
    assert "Add to wishlist" in page


def test_saved_button_posts_to_remove(client, customer, wishlist, product):
    wishlist.add(product)
    client.force_login(customer)

    page = detail_page(client, product)

    assert reverse("wishlist:remove", kwargs={"pk": product.pk}) in page
    assert 'aria-pressed="true"' in page
    assert "On your wishlist" in page
    assert "Remove from your wishlist" in page


def test_button_reflects_only_the_viewers_own_wishlist(
    client, wishlist, product, staff_user
):
    wishlist.add(product)
    client.force_login(staff_user)

    page = detail_page(client, product)

    assert 'aria-pressed="false"' in page


def test_viewing_a_product_creates_no_wishlist(client, customer, product):
    client.force_login(customer)

    detail_page(client, product)

    assert not Wishlist.objects.exists()


def test_unavailable_product_page_shows_the_button(
    client, customer, unavailable_product
):
    client.force_login(customer)

    page = detail_page(client, unavailable_product)

    assert reverse("wishlist:add", kwargs={"pk": unavailable_product.pk}) in page


# --- Add and remove (HTMX) ---------------------------------------------------


@pytest.mark.parametrize("name", ["wishlist:add", "wishlist:remove"])
def test_anonymous_post_redirects_to_login(client, product, name):
    response = client.post(reverse(name, kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url
    assert not Wishlist.objects.exists()


@pytest.mark.parametrize("name", ["wishlist:add", "wishlist:remove"])
def test_get_is_refused(client, customer, product, name):
    client.force_login(customer)

    response = client.get(reverse(name, kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert not WishlistItem.objects.exists()


def test_add_returns_the_saved_button(client, customer, product):
    client.force_login(customer)

    response = client.post(reverse("wishlist:add", kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page
    assert 'aria-pressed="true"' in page
    assert reverse("wishlist:remove", kwargs={"pk": product.pk}) in page
    assert customer.wishlist.items.filter(product=product).exists()


def test_repeated_add_stays_saved(client, customer, product):
    client.force_login(customer)
    client.post(reverse("wishlist:add", kwargs={"pk": product.pk}))

    response = client.post(reverse("wishlist:add", kwargs={"pk": product.pk}))

    assert 'aria-pressed="true"' in response.content.decode()
    assert customer.wishlist.items.count() == 1


def test_add_accepts_an_unavailable_product(client, customer, unavailable_product):
    client.force_login(customer)

    response = client.post(
        reverse("wishlist:add", kwargs={"pk": unavailable_product.pk})
    )

    assert response.status_code == HTTPStatus.OK
    assert customer.wishlist.items.filter(product=unavailable_product).exists()


def test_add_unknown_product_404s(client, customer):
    client.force_login(customer)

    response = client.post(reverse("wishlist:add", kwargs={"pk": 999}))

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_remove_returns_the_unsaved_button(client, customer, wishlist, product):
    wishlist.add(product)
    client.force_login(customer)

    response = client.post(reverse("wishlist:remove", kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page
    assert 'aria-pressed="false"' in page
    assert reverse("wishlist:add", kwargs={"pk": product.pk}) in page
    assert not wishlist.items.exists()


def test_repeated_remove_stays_unsaved(client, customer, product):
    client.force_login(customer)

    response = client.post(reverse("wishlist:remove", kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.OK
    assert 'aria-pressed="false"' in response.content.decode()


def test_staff_save_and_remove_like_customers(client, staff_user, product):
    client.force_login(staff_user)

    client.post(reverse("wishlist:add", kwargs={"pk": product.pk}))
    assert staff_user.wishlist.items.filter(product=product).exists()

    client.post(reverse("wishlist:remove", kwargs={"pk": product.pk}))
    assert not staff_user.wishlist.items.exists()
