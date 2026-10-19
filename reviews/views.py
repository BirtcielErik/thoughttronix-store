"""Review views — thin per the architecture convention.

The rules live on ``Review.objects``; every view re-checks them on the
server, whatever the page showed. Product-page responses render the
"Your review" slot and carry the summary as an out-of-band swap. The
back-office Reviews tab's rows call the same views with
``?surface=backoffice`` and get rows back, with no summary.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views import View
from django.views.generic import ListView

from accounts.mixins import StaffRequiredMixin
from products.models import Product

from .forms import RATING_CHOICES, ModerationForm, ReviewForm
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

    def in_backoffice(self):
        """Whether the request came from a back-office row rather than the
        product page: its URLs carry ``?surface=backoffice``. Only staff
        moderate there, so it answers with rows and never a summary."""
        return (
            self.request.user.is_staff
            and self.request.GET.get("surface") == "backoffice"
        )


class EditReviewView(ReviewLookupMixin, View):
    """HTMX: GET swaps a card for the pre-filled form; POST saves.

    Owners get the full form; a valid save returns the updated card and
    refreshes the summary out-of-band, and an owner with no qualifying order
    left is refused with a 403. Staff skip the purchase check and get the
    comment-only form, so a submitted rating is ignored; their save returns
    just the card, since the numbers can't change. An invalid save returns
    the form with its errors. In the back office the form and the saved
    review are rows.
    """

    def get_review(self):
        review = super().get_review()
        user = self.request.user
        if not user.is_staff and not Review.objects.may_edit(user, review.product):
            raise PermissionDenied
        return review

    def get_form_class(self):
        return ModerationForm if self.request.user.is_staff else ReviewForm

    def get_form_template(self):
        if self.in_backoffice():
            return "reviews/partials/_review_row_form.html"
        return "reviews/partials/_review_edit_form.html"

    def get(self, request, pk):
        review = self.get_review()
        return render(
            request,
            self.get_form_template(),
            {"review": review, "form": self.get_form_class()(instance=review)},
        )

    def post(self, request, pk):
        review = self.get_review()
        form = self.get_form_class()(request.POST, instance=review)
        if not form.is_valid():
            return render(
                request, self.get_form_template(), {"review": review, "form": form}
            )
        form.save()
        if self.in_backoffice():
            return render(
                request, "reviews/partials/_review_row.html", {"review": review}
            )
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
    """HTMX: put the card (or back-office row) back, unchanged, in place of
    the form."""

    def get(self, request, pk):
        review = self.get_review()
        if self.in_backoffice():
            return render(
                request, "reviews/partials/_review_row.html", {"review": review}
            )
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
    In the back office the row disappears the same way, and the heading's
    count (within the page's ``?rating=`` filter) refreshes out-of-band —
    along with the empty state, once that count reaches zero. A delete that
    empties a later page while reviews remain sends the browser to the new
    last page instead.
    """

    def post(self, request, pk):
        review = self.get_review()
        product = review.product
        review.delete()
        if self.in_backoffice():
            rating = rating_filter(request)
            paginator = Paginator(backoffice_reviews(request), REVIEWS_PER_PAGE)
            if paginator.count and page_number(request) > paginator.num_pages:
                response = HttpResponse()
                response["HX-Redirect"] = manage_reviews_url(
                    rating, paginator.num_pages
                )
                return response
            return render(
                request,
                "reviews/partials/_review_deleted.html",
                {"count": paginator.count, "active_rating": rating},
            )
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


# --- The back office --------------------------------------------------------
#
# Staff-only moderation: every review on the site, filterable by rating.
# Its rows edit and delete through the views above, which answer with rows
# instead of cards; the rows' URLs keep the page's ``?rating=`` and
# ``?page=``, so a delete can recount within the filter and notice when it
# has emptied the page. The ``section`` context entry drives the active tab.

RATINGS = [str(stars) for stars, _ in RATING_CHOICES]
REVIEWS_PER_PAGE = 20


def rating_filter(request):
    """The ``?rating=`` filter, or "" when it isn't one of the five stars."""
    rating = request.GET.get("rating", "")
    return rating if rating in RATINGS else ""


def page_number(request):
    """The ``?page=`` number, or 1 when it isn't a number."""
    try:
        return int(request.GET.get("page", 1))
    except ValueError:
        return 1


def manage_reviews_url(rating, page):
    """The Reviews tab's URL at a page within a rating filter."""
    params = {"rating": rating} if rating else {}
    if page > 1:
        params["page"] = page
    url = reverse("reviews:manage_reviews")
    return f"{url}?{urlencode(params)}" if params else url


def backoffice_reviews(request):
    """Every review, narrowed to the request's ``?rating=`` filter if any."""
    reviews = Review.objects.select_related("author", "product")
    if rating := rating_filter(request):
        reviews = reviews.filter(rating=rating)
    return reviews


class ManageReviewListView(StaffRequiredMixin, ListView):
    """All reviews, newest first, filterable via ``?rating=``."""

    template_name = "reviews/manage_reviews.html"
    context_object_name = "reviews"
    paginate_by = REVIEWS_PER_PAGE
    extra_context = {"section": "reviews", "ratings": RATINGS}

    def get_queryset(self):
        return backoffice_reviews(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_rating"] = rating_filter(self.request)
        return context
