"""Wishlist views — thin per the architecture convention.

Add and remove are separate POST-only endpoints rather than one toggle,
so each request means what the customer saw and a repeat is harmless.
Both re-render the product page's wishlist button partial.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import ListView

from products.models import Product

from .models import Wishlist, WishlistItem


class WishlistView(LoginRequiredMixin, ListView):
    """The signed-in customer's wishlist page."""

    template_name = "wishlist/wishlist.html"
    context_object_name = "items"

    def get_queryset(self):
        return WishlistItem.objects.for_user(self.request.user)


class RemoveWishlistItemView(LoginRequiredMixin, View):
    """HTMX: remove a line from the wishlist page; the contents re-render.

    The item is fetched through the owner's wishlist — never by bare pk —
    so another customer's item is a 404.
    """

    def post(self, request, pk):
        items = WishlistItem.objects.for_user(request.user)
        get_object_or_404(items, pk=pk).delete()
        return render(
            request, "wishlist/partials/_wishlist_contents.html", {"items": items}
        )


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
