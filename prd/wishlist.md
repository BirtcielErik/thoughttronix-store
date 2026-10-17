# PRD: The ThoughtTronix Store — Wishlist

*Commissioned by ThoughtTronix Product Management. "Your Thoughts, Our Business."*

---

## Problem Statement

A ThoughtTronix customer who finds a product they like but are not ready to buy has nowhere to keep it. The only place to put a product is the cart, and the cart is for buying: it fills the navbar badge, it is what checkout charges, and it refuses products that are unavailable. So customers either clutter their cart with things they are only considering, or they lose track of the product and have to find it in the catalog again later.

The problem is sharpest for products that are sold out. A customer who wants a product the store cannot sell today has no way to say so, and no way to come back to it when it returns.

The store has the mirror-image problem. Staff can see what sold, but not what customers want and have not bought — including demand for products that are currently unavailable, which is exactly the signal that should drive a restock.

## Solution

A **wishlist** for every customer, plus a demand panel for staff.

**One wishlist per customer.** Every signed-in customer has exactly one wishlist. It is private: nobody else — not other customers, not staff — can see or change its contents.

**Save from the product page.** Next to "Add to cart" on a product's detail page is a wishlist button that always shows the product's current status:

- **♡ Add to wishlist** — the product is not saved; pressing it saves it.
- **♥ On your wishlist** — the product is saved; pressing it removes it.

Pressing the button updates only the button — the page does not reload. Any product can be saved, including one that is currently unavailable. A visitor who is not signed in sees the same "Add to wishlist" label, but it takes them to the sign-in page and brings them back to the product afterwards.

**My wishlist.** A new "Wishlist" link in the navbar, next to "Orders", opens the customer's wishlist page. It lists every saved product, most recently saved first, each with its picture, its name (linking to the product page), its price, whether it is in stock, the usual add-to-cart button, and a **Remove** button. Removing an item takes it off the list without reloading the page. Adding a product to the cart from here leaves it on the wishlist. When the wishlist is empty, the page says so and points the customer back to the catalog.

**Most wishlisted, for staff.** The staff dashboard gains a **Most wishlisted** panel: the five products on the most wishlists right now, each with how many wishlists hold it and an "Unavailable" badge if the store is not currently selling it. Each product links to its back-office edit page. The panel shows aggregate counts only — never which customers saved what. It reflects the present moment, so it does not change with the dashboard's period switcher, and it appears whether or not the store has made any sales yet.

**Demo data.** Resetting the store to the demo world also gives several demo customers wishlists, including at least one unavailable product, so the wishlist pages and the dashboard panel have something to show from the start.

## User Stories

**Visitor (not signed in)**

1. As a visitor, I want to see an "Add to wishlist" button on a product's page, so that I know the store lets me save products for later.
2. As a visitor, I want pressing "Add to wishlist" to send me to sign in and then back to the same product, so that I can save it without hunting for it again.

**Customer (signed in)**

3. As a customer, I want to add a product to my wishlist from its detail page, so that I can come back to it when I am ready to buy.
4. As a customer, I want the wishlist button to update in place without reloading the page, so that I do not lose my place on the product page.
5. As a customer, I want the wishlist button to always show whether the product is on my wishlist, so that I know at a glance whether I have already saved it.
6. As a customer, I want to remove a product from my wishlist by pressing the same button on its detail page, so that I can change my mind where I made the decision.
7. As a customer, I want to save a product that is currently unavailable, so that I can keep track of something I want once it is back in stock.
8. As a customer, I want saving a product I have already saved to leave my wishlist unchanged, so that a double-click or an out-of-date tab never creates duplicates or flips the product back off.
9. As a customer, I want removing a product that is no longer on my wishlist to do nothing harmful, so that a repeated click never shows the wrong status.
10. As a customer, I want a "Wishlist" link in the navbar, so that I can reach my wishlist from any page.
11. As a customer, I want my wishlist page to list every product I have saved, most recently saved first, so that I can review what I was considering.
12. As a customer, I want each wishlist entry to show the product's picture, name, price, and availability, so that I can decide what to do without opening every product.
13. As a customer, I want each product's name on my wishlist to link to its detail page, so that I can read more about it.
14. As a customer, I want to add a wishlist product to my cart directly from my wishlist page, so that buying something I saved takes one click.
15. As a customer, I want a product to stay on my wishlist after I add it to my cart, so that my wishlist is not changed behind my back.
16. As a customer, I want unavailable products on my wishlist clearly marked and not offered for adding to the cart, so that I am not misled into trying to buy them.
17. As a customer, I want to remove a product from my wishlist page without the page reloading, so that tidying my list is quick.
18. As a customer, I want to be able to remove any product from my wishlist, including an unavailable one, so that I am never stuck with an entry I cannot get rid of.
19. As a customer, I want a clear message pointing me to the catalog when my wishlist is empty, including right after I remove the last item, so that I know what to do next.
20. As a customer, I want my wishlist to be private, so that no other customer can see or change what I have saved.
21. As a customer, I want a product the store stops selling entirely to quietly disappear from my wishlist, so that my list never shows products that no longer exist.
22. As a customer using a screen reader, I want the wishlist button to be announced as an on/off toggle, so that I can tell whether the product is saved.

**Employee (staff)**

23. As an employee, I want my own wishlist that works exactly like a customer's, so that I can shop the store like anyone else.
24. As an employee, I want a "Most wishlisted" panel on the dashboard showing the top five products by how many wishlists hold them right now, so that I can see what customers want but have not bought.
25. As an employee, I want unavailable products included in the ranking with an "Unavailable" badge, so that I can spot demand for products worth restocking.
26. As an employee, I want each product in the panel to link to its back-office edit page, so that I can act on what I see immediately.
27. As an employee, I want the panel to stay the same when I switch the dashboard's period, and to say that it shows the present, so that I am not confused about what the number means.
28. As an employee, I want the panel to appear even before the store's first sale, so that I can see early demand right after launch.
29. As an employee, I want a clear message in the panel when nothing has been wishlisted yet, so that an empty panel does not look broken.
30. As an employee, I want the panel to show only how many wishlists hold each product, never whose, so that customers' wishlists stay private.

**Developer**

31. As a developer, I want resetting the demo world to create demo wishlists that include an unavailable product, so that the wishlist pages and the dashboard panel are populated the moment the store is seeded.

## Implementation Decisions

**A new `wishlist` app.** The feature lives in its own app, with its own `wishlist` URL namespace and templates. It depends on the catalog and on accounts; no app's code depends on it except the dashboard's queries and the seed command (both below). This follows the precedent of the coupons app and its one-way import rule.

**Models.**
- `Wishlist` — one per user, by a one-to-one relation to the user, created lazily the first time it is touched via a `for_user` class method, exactly as the cart is.
- `WishlistItem` — a wishlist and a product, unique together, with an `added_at` timestamp. Wishlist pages list items newest first.
- The product relation cascades: deleting a product deletes its wishlist entries. Wishlists are not history, so nothing is snapshotted and nothing protects the product from deletion.
- Saving and removing are model methods on `Wishlist`. Saving is a get-or-create, so it is idempotent; removing a product that is not saved is a no-op.

**URLs and views.** All wishlist views require sign-in and are thin class-based views.
- **Add** and **remove** from the product page are separate POST-only endpoints keyed by product pk. Each performs its one action and re-renders the wishlist button partial. Separate endpoints (rather than one toggle) make each request mean what the customer saw, and make repeats harmless.
- The **add** endpoint looks the product up among all products, not only available ones — deliberately different from add-to-cart.
- The **wishlist page** is a list view of the signed-in customer's items.
- **Remove from the wishlist page** is its own POST-only endpoint keyed by the wishlist item's pk. It fetches the item through the owner's wishlist — never by bare pk — so another customer's item is a 404. It deletes the item and re-renders the wishlist contents partial, mirroring the cart's line-removal view; the empty state therefore appears naturally when the last item goes.

**The wishlist button.** An inclusion template tag in the wishlist app renders the button for a given product, checking that one product's status for the current user. The product detail page loads the tag; the add and remove views render the same partial, so the page's first render and every HTMX update come from one template. This keeps the catalog app's Python free of any wishlist import and avoids a query on every page that a context processor would cost.
- States: signed out — a plain link to sign-in with a `next` back to the product; not saved — an outline "♡ Add to wishlist" button posting to add; saved — a secondary-colored "♥ On your wishlist" button posting to remove, with a tooltip saying it removes.
- The button carries `aria-pressed` reflecting its state.
- It sits beside the add-to-cart button on the detail page; it is shown for unavailable products too.

**The wishlist page.** Extends the base layout. A DaisyUI table in an overflow wrapper with a header row, per the frontend conventions. Each row shows thumbnail, linked name, price, availability badge, the existing add-to-cart partial (reused as-is, fed the product's current cart quantity from the existing cart context), and a Remove button. A designed empty state points to the catalog.

**Navbar.** A plain "Wishlist" link beside "Orders" for signed-in users. No count badge, so there is no per-page query and no out-of-band swap.

**Dashboard.**
- A new `most_wishlisted` function in the dashboard's queries module, taking only a keyword `limit` (default five). It returns products annotated with a `wishlist_count`, highest first. It deliberately takes no `since` cutoff — it answers "right now" — and its docstring says so, since every other query in the module takes one.
- Every wishlist counts, including staff members' own.
- Unavailable products are included.
- The panel sits outside the section gated on the store having sales, so it is always visible, and has its own empty state. It is labelled as showing the present.
- Each row: rank, product name linked to the back-office product edit page, count, and an "Unavailable" badge when applicable. No customer identities appear.

**Seed.** The seed command creates wishlists for several demo customers, including at least one unavailable product. The seed command already imports from accounts, coupons, and orders; adding the wishlist app follows that precedent. Reset is handled by the existing cascades.

**Admin.** Wishlists are not registered in the Django admin.

**Testing.** pytest with plain shared fixtures, per the project convention. Tests cover at least: lazy wishlist creation; idempotent add and remove; adding an unavailable product; the button's rendered state for signed-out, not-saved, and saved; the add/remove endpoints requiring sign-in and POST; owner-scoped removal from the wishlist page (another customer's item is a 404); the empty state after the last removal; cascade on product deletion; the dashboard query's ordering, limit, inclusion of unavailable products, and independence from the period; and the panel rendering with and without sales.

**Documentation.** The project layout section of CLAUDE.md gains the wishlist app. The architecture doc's description of the dashboard queries module is updated if needed to reflect the new function.

## Out of Scope

- **A wishlist button on catalog and category cards.** Deferred. The per-product template tag would run one query per card (an N+1 problem). Doing this properly needs the signed-in user's saved product ids loaded once per page, which means revisiting the button's data-loading approach.
- A wishlist count badge in the navbar.
- "Move to cart" (adding to the cart and removing from the wishlist in one action).
- Notifying customers when a wishlisted product becomes available again, or changes price.
- Multiple or named wishlists per customer.
- Sharing a wishlist, or any public wishlist URL.
- Wishlists for visitors who are not signed in (session-based wishlists), and merging them at sign-in.
- Staff access to any individual customer's wishlist, in the back office or the Django admin.
- Excluding staff wishlists from the dashboard panel.
- A period-filtered or historical view of wishlist activity (adds over time, removals). Only current wishlists are stored.
- Notes, quantities, or priorities on wishlist entries.

## Further Notes

- Unavailable products deliberately behave differently here than in the cart: the cart refuses them because they cannot be bought, but saving a sold-out product for later is a central reason to have a wishlist.
- The "right now" dashboard panel is the one panel that ignores the period switcher; its label must make that clear so staff do not read it as period data.
- The recorded `added_at` timestamp would support a future period-filtered "recently wishlisted" view without a migration, though removals are not recorded.
