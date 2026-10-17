from datetime import timedelta
from http import HTTPStatus

import pytest
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

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


# --- The wishlist page -------------------------------------------------------


def wishlist_page(client):
    return client.get(reverse("wishlist:list")).content.decode()


def test_page_lists_only_the_users_items_newest_first(
    client, customer, wishlist, product, unavailable_product, category, staff_user
):
    # Saved first but backdated, so only added_at (not pk) orders them.
    newer = wishlist.add(product)
    older = wishlist.add(unavailable_product)
    WishlistItem.objects.filter(pk=older.pk).update(
        added_at=timezone.now() - timedelta(days=1)
    )
    someone_elses = category.products.create(
        name="Cortex Cuff", slug="cortex-cuff", price=1
    )
    Wishlist.for_user(staff_user).add(someone_elses)
    client.force_login(customer)

    page = wishlist_page(client)

    assert newer.product.name in page
    assert older.product.name in page
    assert page.index(newer.product.name) < page.index(older.product.name)
    assert "Cortex Cuff" not in page


def test_only_available_products_are_offered_for_the_cart(
    client, customer, wishlist, product, unavailable_product
):
    wishlist.add(product)
    client.force_login(customer)

    page = wishlist_page(client)

    assert reverse("orders:add", kwargs={"pk": product.pk}) in page
    assert "Unavailable" not in page

    wishlist.add(unavailable_product)

    page = wishlist_page(client)

    assert "Unavailable" in page
    assert reverse("orders:add", kwargs={"pk": unavailable_product.pk}) not in page


def test_removing_the_last_item_returns_the_empty_state(
    client, customer, wishlist, product
):
    item = wishlist.add(product)
    client.force_login(customer)

    response = client.post(reverse("wishlist:remove_item", kwargs={"pk": item.pk}))

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page
    assert "Your wishlist is empty" in page
    assert f'href="{reverse("products:catalog")}"' in page
    assert not wishlist.items.exists()


def test_navbar_links_the_wishlist_for_signed_in_users_only(client, customer):
    link = f'href="{reverse("wishlist:list")}"'
    catalog = reverse("products:catalog")

    assert link not in client.get(catalog).content.decode()

    client.force_login(customer)
    assert link in client.get(catalog).content.decode()


def test_anonymous_visitor_to_the_page_is_sent_to_sign_in(client):
    response = client.get(reverse("wishlist:list"))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


def test_page_shows_each_items_details(client, customer, wishlist, product):
    item = wishlist.add(product)
    client.force_login(customer)

    page = wishlist_page(client)

    assert f'src="{product.display_image}"' in page
    assert f'href="{product.get_absolute_url()}"' in page
    assert "$349.99" in page
    assert "In stock" in page
    assert reverse("wishlist:remove_item", kwargs={"pk": item.pk}) in page


def test_empty_wishlist_page_shows_the_empty_state(client, customer):
    client.force_login(customer)

    page = wishlist_page(client)

    assert "Your wishlist is empty" in page
    assert "<table" not in page


def test_adding_to_the_cart_leaves_the_item_on_the_wishlist(
    client, customer, wishlist, product
):
    wishlist.add(product)
    client.force_login(customer)

    client.post(reverse("orders:add", kwargs={"pk": product.pk}))

    assert customer.cart.items.filter(product=product).exists()
    assert wishlist.items.filter(product=product).exists()
    assert "In cart (1)" in wishlist_page(client)


def test_removing_an_unavailable_item_returns_the_remaining_contents(
    client, customer, wishlist, product, unavailable_product
):
    wishlist.add(product)
    item = wishlist.add(unavailable_product)
    client.force_login(customer)

    response = client.post(reverse("wishlist:remove_item", kwargs={"pk": item.pk}))

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page
    assert product.name in page
    assert unavailable_product.name not in page
    assert list(wishlist.items.values_list("product", flat=True)) == [product.pk]


def test_removing_another_customers_item_404s(client, wishlist, product, staff_user):
    item = wishlist.add(product)
    client.force_login(staff_user)

    response = client.post(reverse("wishlist:remove_item", kwargs={"pk": item.pk}))

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert WishlistItem.objects.filter(pk=item.pk).exists()


def test_remove_item_redirects_anonymous_visitors(client, wishlist, product):
    item = wishlist.add(product)

    response = client.post(reverse("wishlist:remove_item", kwargs={"pk": item.pk}))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url
    assert WishlistItem.objects.filter(pk=item.pk).exists()


def test_remove_item_refuses_get(client, customer, wishlist, product):
    item = wishlist.add(product)
    client.force_login(customer)

    response = client.get(reverse("wishlist:remove_item", kwargs={"pk": item.pk}))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert WishlistItem.objects.filter(pk=item.pk).exists()


def test_deleting_a_product_removes_it_from_every_wishlist(
    wishlist, product, staff_user
):
    wishlist.add(product)
    Wishlist.for_user(staff_user).add(product)

    product.delete()

    assert not WishlistItem.objects.exists()
