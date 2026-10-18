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
                "summary": Review.objects.summary(product),
                "oob_summary": True,
            },
        )
