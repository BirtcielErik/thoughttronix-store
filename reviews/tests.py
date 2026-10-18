import re
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from orders.models import Order

from .models import Review, ReviewQuerySet


def buy(user, product, status=Order.Status.PLACED):
    """One order of ``product`` for ``user``, with the addresses boilerplate."""
    order = Order.objects.create(
        user=user,
        status=status,
        total=product.price,
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
    )
    order.items.create(
        product=product,
        product_name=product.name,
        unit_price=Decimal(product.price),
        quantity=1,
    )
    return order


# --- Eligibility --------------------------------------------------------------


@pytest.mark.parametrize(
    ("viewer", "status", "reviewed", "expected"),
    [
        ("customer", Order.Status.PLACED, False, True),
        ("customer", Order.Status.SHIPPED, False, True),
        ("customer", Order.Status.DELIVERED, False, True),
        ("customer", Order.Status.CANCELLED, False, False),
        ("customer", None, False, False),
        ("customer", Order.Status.PLACED, True, False),
        ("staff_user", Order.Status.PLACED, False, False),
        ("anonymous", None, False, False),
    ],
)
def test_can_create(request, product, viewer, status, reviewed, expected):
    if viewer == "anonymous":
        user = AnonymousUser()
    else:
        user = request.getfixturevalue(viewer)
    if status:
        buy(user, product, status)
    if reviewed:
        Review.objects.create(author=user, product=product, rating=5, comment="Yes.")

    assert Review.objects.can_create(user, product) is expected


def test_one_live_order_is_enough_beside_a_cancelled_one(customer, product):
    buy(customer, product, Order.Status.CANCELLED)
    buy(customer, product, Order.Status.DELIVERED)

    assert Review.objects.can_create(customer, product)


def test_an_unavailable_product_can_be_reviewed(customer, unavailable_product):
    buy(customer, unavailable_product)

    assert Review.objects.can_create(customer, unavailable_product)


def test_buying_a_different_product_does_not_qualify(customer, product, category):
    other = category.products.create(name="Cortex Cuff", slug="cortex-cuff", price=1)
    buy(customer, other)

    assert not Review.objects.can_create(customer, product)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (Order.Status.PLACED, True),
        (Order.Status.SHIPPED, True),
        (Order.Status.DELIVERED, True),
        (Order.Status.CANCELLED, False),
        (None, False),
    ],
)
def test_may_edit_follows_the_purchase_check(customer, product, status, expected):
    if status:
        buy(customer, product, status)
    Review.objects.create(author=customer, product=product, rating=3, comment="Ok.")

    assert Review.objects.may_edit(customer, product) is expected


def test_anonymous_users_may_not_edit(product):
    assert not Review.objects.may_edit(AnonymousUser(), product)


# --- The review itself --------------------------------------------------------


def test_one_review_per_author_and_product(customer, product):
    Review.objects.create(author=customer, product=product, rating=5, comment="A")

    with pytest.raises(IntegrityError):
        Review.objects.create(author=customer, product=product, rating=1, comment="B")


def test_deleting_the_product_deletes_its_reviews(customer, product):
    Review.objects.create(author=customer, product=product, rating=5, comment="A")

    product.delete()

    assert not Review.objects.exists()


def test_deleting_the_author_deletes_their_reviews(customer, product):
    Review.objects.create(author=customer, product=product, rating=5, comment="A")

    customer.delete()

    assert not Review.objects.exists()


def test_summary_averages_the_products_ratings(customer, product, nova_review):
    Review.objects.create(author=customer, product=product, rating=2, comment="Meh.")
    elsewhere = product.category.products.create(name="X", slug="x", price=1)
    Review.objects.create(author=customer, product=elsewhere, rating=1, comment="No.")

    summary = Review.objects.summary(product)

    assert summary["average"] == 3.5
    assert summary["count"] == 2
    assert summary["stars"] == 4


def test_summary_of_a_product_with_no_reviews(product):
    assert Review.objects.summary(product) == {"average": None, "count": 0, "stars": 0}


def test_was_edited_only_after_a_later_save(customer, product):
    review = Review.objects.create(
        author=customer, product=product, rating=4, comment="Good hub."
    )
    review.refresh_from_db()

    assert not review.was_edited

    # Posted an hour ago, then changed now.
    an_hour_ago = timezone.now() - timedelta(hours=1)
    Review.objects.filter(pk=review.pk).update(
        created_at=an_hour_ago, updated_at=an_hour_ago
    )
    review.refresh_from_db()
    review.comment = "Good hub. Listens a little too well."
    review.save()
    review.refresh_from_db()

    assert review.was_edited


# --- The reviews section on the product page ----------------------------------


@pytest.fixture
def nova_review(product):
    """Another customer's review, which every viewer should see in the list."""
    nova = get_user_model().objects.create_user(
        username="nova", password="x", first_name="Nova", last_name="Kepler"
    )
    buy(nova, product)
    return Review.objects.create(
        author=nova, product=product, rating=5, comment="Finally, someone listens."
    )


def reviews_parts(client, product):
    """The "Your review" slot (None when absent) and the list below it."""
    page = client.get(product.get_absolute_url()).content.decode()
    list_start = page.index('id="review-list"')
    listing = page[list_start:]
    if 'id="your-review"' not in page:
        return None, listing
    return page[page.index('id="your-review"') : list_start], listing


@pytest.mark.parametrize(
    ("viewer", "in_slot"),
    [
        (
            "visitor",
            [
                "Sign in to review",
                'href="{login}?next=/products/seraphine-home-hub/"',
            ],
        ),
        ("non-buyer", ["Only customers who bought this product can review it"]),
        ("reviewer", ["My hub hears everything."]),
        ("staff", None),
    ],
)
def test_your_review_slot_by_viewer(
    client, customer, staff_user, product, nova_review, viewer, in_slot
):
    if viewer == "reviewer":
        buy(customer, product)
        Review.objects.create(
            author=customer,
            product=product,
            rating=4,
            comment="My hub hears everything.",
        )
    if viewer in ("non-buyer", "reviewer"):
        client.force_login(customer)
    if viewer == "staff":
        client.force_login(staff_user)

    slot, listing = reviews_parts(client, product)

    if in_slot is None:
        assert slot is None
    else:
        assert slot is not None
        for text in in_slot:
            assert text.format(login=reverse("accounts:login")) in slot
    # The list shows everyone else, never the viewer's own review again.
    assert "Finally, someone listens." in listing
    assert "My hub hears everything." not in listing


def test_eligible_customer_sees_the_form(client, customer, product):
    buy(customer, product)
    client.force_login(customer)

    slot, _ = reviews_parts(client, product)

    assert f'hx-post="{reverse("reviews:create", args=[product.pk])}"' in slot
    assert 'name="rating"' in slot
    assert 'name="comment"' in slot
    assert "Only customers who bought" not in slot
    assert "Sign in to review" not in slot


def test_staff_see_their_own_earlier_review_in_the_list(client, staff_user, product):
    Review.objects.create(
        author=staff_user, product=product, rating=3, comment="Bought it pre-promotion."
    )
    client.force_login(staff_user)

    slot, listing = reviews_parts(client, product)

    assert slot is None
    assert "Bought it pre-promotion." in listing


def test_card_shows_stars_name_date_and_comment(client, product, nova_review):
    page = client.get(product.get_absolute_url()).content.decode()

    assert 'aria-label="5 out of 5 stars"' in page
    assert "Nova K." in page
    assert "Kepler" not in page
    assert nova_review.created_at.strftime("%b") in page
    assert "Finally, someone listens." in page
    assert "(edited)" not in page


def test_card_marks_an_edited_review(client, product, nova_review):
    an_hour_ago = timezone.now() - timedelta(hours=1)
    Review.objects.filter(pk=nova_review.pk).update(created_at=an_hour_ago)

    page = client.get(product.get_absolute_url()).content.decode()

    assert "(edited)" in page


def test_list_is_newest_first(client, product, nova_review):
    older = get_user_model().objects.create_user(username="ada", first_name="Ada")
    buy(older, product)
    # Created after Nova's but backdated, so only created_at orders them.
    Review.objects.create(
        author=older,
        product=product,
        rating=2,
        comment="Older opinion.",
        created_at=timezone.now() - timedelta(days=3),
    )

    _, listing = reviews_parts(client, product)

    assert listing.index("Finally, someone listens.") < listing.index("Older opinion.")


def test_page_summary_shows_average_and_count(client, customer, product, nova_review):
    Review.objects.create(author=customer, product=product, rating=2, comment="Meh.")

    page = client.get(product.get_absolute_url()).content.decode()

    assert "3.5" in page
    assert "(2 reviews)" in page


def test_page_with_no_reviews_says_so(client, product):
    page = client.get(product.get_absolute_url()).content.decode()

    assert "No reviews yet." in page


def test_unavailable_product_page_shows_its_reviews(
    client, customer, unavailable_product
):
    buy(customer, unavailable_product)
    Review.objects.create(
        author=customer, product=unavailable_product, rating=4, comment="Still mine."
    )

    page = client.get(unavailable_product.get_absolute_url()).content.decode()

    assert "Still mine." in page
    assert "(1 review)" in page


def test_review_stays_up_after_its_order_is_cancelled(client, customer, product):
    order = buy(customer, product)
    Review.objects.create(
        author=customer, product=product, rating=4, comment="Kept my word."
    )
    order.status = Order.Status.CANCELLED
    order.save()

    _, listing = reviews_parts(client, product)
    assert "Kept my word." in listing

    client.force_login(customer)
    slot, _ = reviews_parts(client, product)
    assert "Kept my word." in slot


# --- Writing a review ---------------------------------------------------------


def post_review(client, product, **data):
    return client.post(reverse("reviews:create", args=[product.pk]), data)


def test_valid_review_returns_the_slot_and_an_oob_summary(
    client, customer, product, nova_review
):
    buy(customer, product)
    client.force_login(customer)

    response = post_review(client, product, rating=2, comment="Too attentive.")

    assert Review.objects.filter(
        author=customer, product=product, rating=2, comment="Too attentive."
    ).exists()
    page = response.content.decode()
    # The slot now shows the review, not the form...
    assert "Too attentive." in page
    assert 'name="comment"' not in page
    # ...and the summary swaps out-of-band with Nova's 5 and this 2.
    assert re.search(r'<div id="review-summary"[^>]*hx-swap-oob="true"', page)
    assert "3.5" in page
    assert "(2 reviews)" in page


@pytest.mark.parametrize("viewer", ["non-buyer", "reviewer", "staff"])
def test_ineligible_reviewers_are_refused(
    client, customer, staff_user, product, viewer
):
    user = staff_user if viewer == "staff" else customer
    if viewer != "non-buyer":
        buy(user, product)
    if viewer == "reviewer":
        Review.objects.create(
            author=user, product=product, rating=4, comment="Said my piece."
        )
    client.force_login(user)

    response = post_review(client, product, rating=1, comment="Again!")

    assert response.status_code == 403
    assert not Review.objects.filter(comment="Again!").exists()


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ({"comment": "Fine."}, "Choose a star rating."),
        ({"rating": "", "comment": "Fine."}, "Choose a star rating."),
        ({"rating": 6, "comment": "Fine."}, "Select a valid choice."),
        ({"rating": 0, "comment": "Fine."}, "Select a valid choice."),
        ({"rating": 4}, "Write a comment."),
        ({"rating": 4, "comment": "   \n "}, "Write a comment."),
        ({"rating": 4, "comment": "x" * 2001}, "at most 2000 characters"),
    ],
)
def test_invalid_review_re_renders_the_form_with_its_error(
    client, customer, product, data, error
):
    buy(customer, product)
    client.force_login(customer)

    response = post_review(client, product, **data)

    assert response.status_code == 200
    page = response.content.decode()
    assert 'name="comment"' in page
    assert error in page
    # Nothing changed, so the summary isn't refreshed.
    assert "hx-swap-oob" not in page
    assert not Review.objects.exists()


def test_invalid_review_keeps_what_was_entered(client, customer, product):
    buy(customer, product)
    client.force_login(customer)

    page = post_review(client, product, rating=4, comment="").content.decode()

    assert re.search(r'value="4"[^>]*checked', page)


def test_a_comment_of_exactly_2000_characters_is_accepted(client, customer, product):
    buy(customer, product)
    client.force_login(customer)

    post_review(client, product, rating=4, comment="x" * 2000)

    assert Review.objects.filter(author=customer).exists()


def test_an_unavailable_product_can_be_reviewed_from_its_page(
    client, customer, unavailable_product
):
    buy(customer, unavailable_product, Order.Status.DELIVERED)
    client.force_login(customer)

    response = post_review(client, unavailable_product, rating=3, comment="Gone.")

    assert response.status_code == 200
    assert Review.objects.filter(product=unavailable_product).exists()


def test_create_redirects_anonymous_visitors_to_sign_in(client, product):
    response = post_review(client, product, rating=5, comment="Hi.")

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))
    assert not Review.objects.exists()


def test_create_refuses_get(client, customer, product):
    buy(customer, product)
    client.force_login(customer)

    response = client.get(reverse("reviews:create", args=[product.pk]))

    assert response.status_code == 405


def test_create_of_an_unknown_product_is_a_404(client, customer):
    client.force_login(customer)

    response = client.post(reverse("reviews:create", args=[999]), {"rating": 5})

    assert response.status_code == 404


def test_a_double_submit_is_refused_not_an_error(
    client, customer, product, monkeypatch
):
    # The second of two racing requests: it passed can_create before the
    # first one saved.
    buy(customer, product)
    Review.objects.create(author=customer, product=product, rating=5, comment="1st")
    monkeypatch.setattr(ReviewQuerySet, "can_create", lambda self, user, p: True)
    client.force_login(customer)

    response = post_review(client, product, rating=5, comment="2nd")

    assert response.status_code == 403
    assert Review.objects.count() == 1


# --- Editing and deleting your own review -------------------------------------


@pytest.mark.parametrize(
    ("method", "name", "data"),
    [
        ("get", "reviews:edit", {}),
        ("post", "reviews:edit", {"rating": 1, "comment": "Hijacked."}),
        ("get", "reviews:cancel", {}),
        ("post", "reviews:delete", {}),
    ],
)
def test_another_customers_review_is_a_404(
    client, customer, product, nova_review, method, name, data
):
    buy(customer, product)
    client.force_login(customer)

    response = getattr(client, method)(reverse(name, args=[nova_review.pk]), data)

    assert response.status_code == 404
    nova_review.refresh_from_db()
    assert nova_review.rating == 5
    assert nova_review.comment == "Finally, someone listens."


def test_owner_whose_only_order_was_cancelled_can_delete_but_not_edit(
    client, customer, product
):
    order = buy(customer, product)
    review = Review.objects.create(
        author=customer, product=product, rating=4, comment="Kept my word."
    )
    order.status = Order.Status.CANCELLED
    order.save()
    client.force_login(customer)
    edit_url = reverse("reviews:edit", args=[review.pk])

    assert client.get(edit_url).status_code == 403
    response = client.post(edit_url, {"rating": 1, "comment": "Changed my mind."})
    assert response.status_code == 403
    review.refresh_from_db()
    assert (review.rating, review.comment) == (4, "Kept my word.")

    response = client.post(reverse("reviews:delete", args=[review.pk]))

    assert response.status_code == 200
    assert not Review.objects.exists()
    page = response.content.decode()
    assert "Only customers who bought this product can review it" in page
    assert 'name="comment"' not in page


@pytest.fixture
def own_review(customer, product):
    """The signed-in customer's review of a product they bought, posted an
    hour ago so a save now counts as an edit."""
    buy(customer, product)
    an_hour_ago = timezone.now() - timedelta(hours=1)
    review = Review.objects.create(
        author=customer, product=product, rating=4, comment="My hub hears everything."
    )
    Review.objects.filter(pk=review.pk).update(
        created_at=an_hour_ago, updated_at=an_hour_ago
    )
    review.refresh_from_db()
    return review


def test_own_review_card_has_edit_and_delete(client, customer, product, own_review):
    client.force_login(customer)

    slot, _ = reviews_parts(client, product)

    assert f'hx-get="{reverse("reviews:edit", args=[own_review.pk])}"' in slot
    assert f'hx-post="{reverse("reviews:delete", args=[own_review.pk])}"' in slot
    assert "hx-confirm=" in slot


def test_no_edit_button_once_the_only_order_is_cancelled(
    client, customer, product, own_review
):
    Order.objects.update(status=Order.Status.CANCELLED)
    client.force_login(customer)

    slot, _ = reviews_parts(client, product)

    assert reverse("reviews:edit", args=[own_review.pk]) not in slot
    assert reverse("reviews:delete", args=[own_review.pk]) in slot


def test_other_customers_cards_have_no_actions(client, customer, product, nova_review):
    buy(customer, product)
    client.force_login(customer)

    _, listing = reviews_parts(client, product)

    assert reverse("reviews:edit", args=[nova_review.pk]) not in listing
    assert reverse("reviews:delete", args=[nova_review.pk]) not in listing


def test_edit_returns_the_prefilled_form(client, customer, own_review):
    client.force_login(customer)

    response = client.get(reverse("reviews:edit", args=[own_review.pk]))

    page = response.content.decode()
    assert f'id="review-{own_review.pk}"' in page
    assert f'hx-post="{reverse("reviews:edit", args=[own_review.pk])}"' in page
    assert re.search(r'value="4"[^>]*checked', page)
    assert "My hub hears everything." in page
    assert reverse("reviews:cancel", args=[own_review.pk]) in page


def test_save_returns_the_edited_card_and_an_oob_summary(
    client, customer, own_review, nova_review
):
    client.force_login(customer)

    response = client.post(
        reverse("reviews:edit", args=[own_review.pk]),
        {"rating": 2, "comment": "It hears too much."},
    )

    own_review.refresh_from_db()
    assert (own_review.rating, own_review.comment) == (2, "It hears too much.")
    page = response.content.decode()
    assert f'<article id="review-{own_review.pk}"' in page
    assert "It hears too much." in page
    assert "(edited)" in page
    assert 'name="comment"' not in page
    # Nova's 5 and the new 2.
    assert re.search(r'<div id="review-summary"[^>]*hx-swap-oob="true"', page)
    assert "3.5" in page
    assert "(2 reviews)" in page


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ({"comment": "Fine."}, "Choose a star rating."),
        ({"rating": 9, "comment": "Fine."}, "Select a valid choice."),
        ({"rating": 2, "comment": "  "}, "Write a comment."),
        ({"rating": 2, "comment": "x" * 2001}, "at most 2000 characters"),
    ],
)
def test_invalid_save_returns_the_form_and_changes_nothing(
    client, customer, own_review, data, error
):
    client.force_login(customer)

    response = client.post(reverse("reviews:edit", args=[own_review.pk]), data)

    assert response.status_code == 200
    page = response.content.decode()
    assert 'name="comment"' in page
    assert error in page
    assert "hx-swap-oob" not in page
    own_review.refresh_from_db()
    assert (own_review.rating, own_review.comment) == (4, "My hub hears everything.")


def test_cancel_returns_the_card_unchanged(client, customer, own_review):
    client.force_login(customer)

    response = client.get(reverse("reviews:cancel", args=[own_review.pk]))

    page = response.content.decode()
    assert f'<article id="review-{own_review.pk}"' in page
    assert "My hub hears everything." in page
    assert 'name="comment"' not in page
    assert reverse("reviews:edit", args=[own_review.pk]) in page
    assert "hx-swap-oob" not in page


def test_delete_brings_the_form_back_and_refreshes_the_summary(
    client, customer, product, own_review, nova_review
):
    client.force_login(customer)

    response = client.post(reverse("reviews:delete", args=[own_review.pk]))

    assert not Review.objects.filter(pk=own_review.pk).exists()
    page = response.content.decode()
    assert f'hx-post="{reverse("reviews:create", args=[product.pk])}"' in page
    assert "My hub hears everything." not in page
    # Only Nova's 5 is left.
    assert re.search(r'<div id="review-summary"[^>]*hx-swap-oob="true"', page)
    assert "5.0" in page
    assert "(1 review)" in page


def test_deleting_the_last_review_says_no_reviews(client, customer, own_review):
    client.force_login(customer)

    response = client.post(reverse("reviews:delete", args=[own_review.pk]))

    assert "No reviews yet." in response.content.decode()


@pytest.mark.parametrize(
    ("method", "name"),
    [
        ("get", "reviews:edit"),
        ("post", "reviews:edit"),
        ("get", "reviews:cancel"),
        ("post", "reviews:delete"),
    ],
)
def test_edit_cancel_and_delete_redirect_anonymous_visitors(
    client, own_review, method, name
):
    response = getattr(client, method)(
        reverse(name, args=[own_review.pk]), {"rating": 1, "comment": "Anon."}
    )

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))
    own_review.refresh_from_db()
    assert own_review.comment == "My hub hears everything."


def test_delete_refuses_get(client, customer, own_review):
    client.force_login(customer)

    response = client.get(reverse("reviews:delete", args=[own_review.pk]))

    assert response.status_code == 405
    assert Review.objects.filter(pk=own_review.pk).exists()


def test_cancel_refuses_post(client, customer, own_review):
    client.force_login(customer)

    response = client.post(reverse("reviews:cancel", args=[own_review.pk]))

    assert response.status_code == 405


# --- Stars in the catalog -----------------------------------------------------


@pytest.mark.parametrize("listing", ["catalog", "category"])
def test_catalog_cards_show_average_and_count(
    client, customer, product, nova_review, listing
):
    Review.objects.create(author=customer, product=product, rating=2, comment="Meh.")
    product.category.products.create(name="Cortex Cuff", slug="cortex-cuff", price=1)
    if listing == "catalog":
        url = reverse("products:catalog")
    else:
        url = product.category.get_absolute_url()

    page = client.get(url).content.decode()

    # Seraphine's card: Nova's 5 and this 2.
    assert 'aria-label="4 out of 5 stars"' in page
    assert "3.5" in page
    assert "(2 reviews)" in page
    # The Cortex Cuff is listed, but with no reviews it shows no stars.
    assert "Cortex Cuff" in page
    assert page.count("out of 5 stars") == 1
