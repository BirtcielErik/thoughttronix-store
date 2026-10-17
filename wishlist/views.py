"""Wishlist views — thin per the architecture convention.

Add and remove are separate POST-only endpoints rather than one toggle,
so each request means what the customer saw and a repeat is harmless.
Both re-render the product page's wishlist button partial.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View

from products.models import Product

from .models import Wishlist


class WishlistButtonView(LoginRequiredMixin, View):
    """Base for the button's HTMX actions: act, then re-render the button.

    Looks the product up among all products, not ``available()`` —
    deliberately unlike add-to-cart, since saving a sold-out product for
    later is a central reason to have a wishlist.
    """

    saved = None

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        self.act(Wishlist.for_user(request.user), product)
        return render(
            request,
            "wishlist/partials/_wishlist_button.html",
            {"product": product, "saved": self.saved},
        )

    def act(self, wishlist, product):
        raise NotImplementedError


class AddToWishlistView(WishlistButtonView):
    saved = True

    def act(self, wishlist, product):
        wishlist.add(product)


class RemoveFromWishlistView(WishlistButtonView):
    saved = False

    def act(self, wishlist, product):
        wishlist.remove(product)
