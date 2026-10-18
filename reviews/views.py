"""Review views — thin per the architecture convention.

The rules live on ``Review.objects``; every view re-checks them on the
server, whatever the page showed. Product-page responses render the
"Your review" slot and carry the summary as an out-of-band swap.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, render
from django.views import View

from products.models import Product

from .forms import ReviewForm
from .models import Review


class CreateReviewView(LoginRequiredMixin, View):
    """HTMX: post a new review from the "Your review" slot.

    Looks the product up among all products, so a customer can review one
    the store no longer sells. An ineligible request is a 403 and creates
    nothing; an invalid form re-renders the slot with its errors.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        if not Review.objects.can_create(request.user, product):
            raise PermissionDenied
        form = ReviewForm(
            request.POST, instance=Review(author=request.user, product=product)
        )
        if not form.is_valid():
            return render(
                request,
                "reviews/partials/_your_review.html",
                {
                    "product": product,
                    "user": request.user,
                    "can_create": True,
                    "form": form,
                },
            )
        try:
            with transaction.atomic():
                review = form.save()
        except IntegrityError:
            # A double submit: both requests passed can_create, and the
            # database's one-review-per-product constraint stopped the second.
            raise PermissionDenied from None
        return render(
            request,
            "reviews/partials/_your_review.html",
            {
                "product": product,
                "user": request.user,
                "own_review": review,
                "own_can_edit": True,
                "summary": Review.objects.summary(product),
                "oob_summary": True,
            },
        )


class OwnReviewMixin(LoginRequiredMixin):
    """Fetches the review named in the URL for a customer acting on it.

    The review is fetched through the customer's own reviews — never by
    bare pk — so another customer's review is a 404.
    """

    def get_review(self):
        return get_object_or_404(
            self.request.user.reviews.select_related("author", "product"),
            pk=self.kwargs["pk"],
        )


class EditReviewView(OwnReviewMixin, View):
    """HTMX: GET swaps the owner's card for the pre-filled form; POST saves.

    A valid save returns the updated card and refreshes the summary
    out-of-band; an invalid one returns the form with its errors. An owner
    with no qualifying order left is refused with a 403 and changes nothing.
    """

    def get_review(self):
        review = super().get_review()
        if not Review.objects.may_edit(self.request.user, review.product):
            raise PermissionDenied
        return review

    def get(self, request, pk):
        review = self.get_review()
        return render(
            request,
            "reviews/partials/_review_edit_form.html",
            {"review": review, "form": ReviewForm(instance=review)},
        )

    def post(self, request, pk):
        review = self.get_review()
        form = ReviewForm(request.POST, instance=review)
        if not form.is_valid():
            return render(
                request,
                "reviews/partials/_review_edit_form.html",
                {"review": review, "form": form},
            )
        form.save()
        return render(
            request,
            "reviews/partials/_review_saved.html",
            {
                "review": review,
                "can_edit": True,
                "can_delete": True,
                "summary": Review.objects.summary(review.product),
            },
        )


class CancelEditReviewView(OwnReviewMixin, View):
    """HTMX: put the owner's card back, unchanged, in place of the form."""

    def get(self, request, pk):
        review = self.get_review()
        return render(
            request,
            "reviews/partials/_review_card.html",
            {
                "review": review,
                "can_edit": Review.objects.may_edit(request.user, review.product),
                "can_delete": True,
            },
        )


class DeleteReviewView(OwnReviewMixin, View):
    """HTMX: delete the owner's review and refill the "Your review" slot.

    Always allowed for the owner. The slot falls back to the form if they
    still qualify to review the product, or the non-buyer message if not.
    """

    def post(self, request, pk):
        review = self.get_review()
        product = review.product
        review.delete()
        can_create = Review.objects.can_create(request.user, product)
        return render(
            request,
            "reviews/partials/_your_review.html",
            {
                "product": product,
                "user": request.user,
                "can_create": can_create,
                "form": ReviewForm() if can_create else None,
                "summary": Review.objects.summary(product),
                "oob_summary": True,
            },
        )
