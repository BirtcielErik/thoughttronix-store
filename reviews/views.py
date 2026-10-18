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

from .forms import ModerationForm, ReviewForm
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


class ReviewLookupMixin(LoginRequiredMixin):
    """Fetches the review named in the URL for the user acting on it.

    Staff are moderators and look among all reviews. A customer's lookup
    goes through their own reviews — never by bare pk — so another
    customer's review is a 404.
    """

    def get_review(self):
        user = self.request.user
        reviews = Review.objects.all() if user.is_staff else user.reviews.all()
        return get_object_or_404(
            reviews.select_related("author", "product"), pk=self.kwargs["pk"]
        )


class EditReviewView(ReviewLookupMixin, View):
    """HTMX: GET swaps a card for the pre-filled form; POST saves.

    Owners get the full form; a valid save returns the updated card and
    refreshes the summary out-of-band, and an owner with no qualifying order
    left is refused with a 403. Staff skip the purchase check and get the
    comment-only form, so a submitted rating is ignored; their save returns
    just the card, since the numbers can't change. An invalid save returns
    the form with its errors.
    """

    def get_review(self):
        review = super().get_review()
        user = self.request.user
        if not user.is_staff and not Review.objects.may_edit(user, review.product):
            raise PermissionDenied
        return review

    def get_form_class(self):
        return ModerationForm if self.request.user.is_staff else ReviewForm

    def get(self, request, pk):
        review = self.get_review()
        return render(
            request,
            "reviews/partials/_review_edit_form.html",
            {"review": review, "form": self.get_form_class()(instance=review)},
        )

    def post(self, request, pk):
        review = self.get_review()
        form = self.get_form_class()(request.POST, instance=review)
        if not form.is_valid():
            return render(
                request,
                "reviews/partials/_review_edit_form.html",
                {"review": review, "form": form},
            )
        form.save()
        if request.user.is_staff:
            return render(
                request,
                "reviews/partials/_review_card.html",
                {"review": review, "can_edit": True, "can_delete": True},
            )
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


class CancelEditReviewView(ReviewLookupMixin, View):
    """HTMX: put the card back, unchanged, in place of the form."""

    def get(self, request, pk):
        review = self.get_review()
        user = request.user
        return render(
            request,
            "reviews/partials/_review_card.html",
            {
                "review": review,
                "can_edit": user.is_staff
                or Review.objects.may_edit(user, review.product),
                "can_delete": True,
            },
        )


class DeleteReviewView(ReviewLookupMixin, View):
    """HTMX: delete a review and send back what replaces it.

    Always allowed for the owner, whose "Your review" slot falls back to the
    form if they still qualify to review the product, or the non-buyer
    message if not. A staff delete sends back nothing in place of the card,
    so it disappears from the list. Both refresh the summary out-of-band.
    """

    def post(self, request, pk):
        review = self.get_review()
        product = review.product
        review.delete()
        if request.user.is_staff:
            return render(
                request,
                "reviews/partials/_summary.html",
                {"summary": Review.objects.summary(product), "oob": True},
            )
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
