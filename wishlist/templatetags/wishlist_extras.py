from django import template

from wishlist.models import WishlistItem

register = template.Library()


@register.inclusion_tag("wishlist/partials/_wishlist_button.html", takes_context=True)
def wishlist_button(context, product):
    """Render the wishlist button for one product, in its current state.

    The add and remove views render the same partial, so the first render
    and every HTMX update share one template. Checks only this product —
    no wishlist is created just by viewing a page.
    """
    user = context["user"]
    saved = (
        user.is_authenticated
        and WishlistItem.objects.filter(wishlist__user=user, product=product).exists()
    )
    return {"product": product, "saved": saved, "user": user}
