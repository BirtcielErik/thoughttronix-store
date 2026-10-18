from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count
from django.utils import timezone

from orders.models import Order
from products.models import Product

# How much later than posting a save must be to label a review "(edited)".
EDIT_TOLERANCE = timedelta(minutes=1)


def whole_stars(average):
    """An average rating as whole stars for display, rounded half up.

    Not ``round()``, which would show 2.5 as two stars. No average (no
    reviews) is no stars.
    """
    return int(average + 0.5) if average is not None else 0


def _has_purchased(user, product):
    # "Purchased" means what it means on the dashboard: any order status
    # except cancelled. No delivery needed, and availability is irrelevant.
    return (
        Order.objects.filter(user=user, items__product=product)
        .exclude(status=Order.Status.CANCELLED)
        .exists()
    )


class ReviewQuerySet(models.QuerySet):
    def can_create(self, user, product):
        """Whether ``user`` may write a new review of ``product``.

        Signed in, not staff (staff moderate, never review), at least one
        non-cancelled order containing the product, and no review of it yet.
        """
        return (
            user.is_authenticated
            and not user.is_staff
            and _has_purchased(user, product)
            and not self.filter(author=user, product=product).exists()
        )

    def may_edit(self, user, product):
        """Whether ``user`` still qualifies to edit their review of ``product``.

        The purchase check alone: an owner whose only order was cancelled
        keeps the review but can no longer change it. Staff moderate under
        their own rules and never come through here.
        """
        return user.is_authenticated and _has_purchased(user, product)

    def summary(self, product):
        """``{"average", "stars", "count"}`` for ``product``'s reviews.

        ``average`` is None (and ``stars`` 0) when there are none; ``stars``
        is the average as whole stars for display (see ``whole_stars``).
        """
        summary = self.filter(product=product).aggregate(
            average=Avg("rating"), count=Count("pk")
        )
        summary["stars"] = whole_stars(summary["average"])
        return summary


class Review(models.Model):
    """A verified buyer's star rating and comment on one product.

    One per customer per product, enforced by the database. Like wishlist
    entries, reviews are not history: nothing is snapshotted, and deleting
    the product or the author deletes the review.
    """

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(max_length=2000)
    # default (not auto_now_add) so the seed can backdate reviews.
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ReviewQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["author", "product"], name="unique_review_author_product"
            )
        ]

    def __str__(self):
        return f"{self.rating}★ {self.product.name} by {self.author.username}"

    @property
    def was_edited(self):
        """Whether the review changed after it was posted — the "(edited)" label.

        ``created_at`` is set when the review is built and ``updated_at`` when
        it is saved, so even a fresh review has them microseconds apart; the
        tolerance keeps creation itself from counting.
        """
        return self.updated_at - self.created_at > EDIT_TOLERANCE
