from django import template

from reviews import models
from reviews.forms import ReviewForm
from reviews.models import Review

register = template.Library()


@register.filter
def whole_stars(average):
    """An average rating as whole stars, for cards that carry an annotated
    average rather than a summary."""
    return models.whole_stars(average)


@register.inclusion_tag("reviews/partials/_reviews_section.html", takes_context=True)
def reviews_section(context, product):
    """Render a product's reviews: the summary, the "Your review" slot, the list.

    The review views will render the same partials, so the first render and
    every HTMX update share one set of templates. Staff are moderators, never
    reviewers, so they get no slot, and any review they once wrote as a
    customer stays in the list.
    """
    user = context["user"]
    reviews = product.reviews.select_related("author")
    show_slot = not user.is_staff
    own_review = None
    if show_slot and user.is_authenticated:
        own_review = reviews.filter(author=user).first()
    if own_review:
        reviews = reviews.exclude(pk=own_review.pk)
    can_create = own_review is None and Review.objects.can_create(user, product)
    return {
        "product": product,
        "user": user,
        "summary": Review.objects.summary(product),
        "reviews": reviews,
        "show_slot": show_slot,
        "own_review": own_review,
        "can_create": can_create,
        "form": ReviewForm() if can_create else None,
    }
