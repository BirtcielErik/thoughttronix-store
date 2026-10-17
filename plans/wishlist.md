# Plan: The ThoughtTronix Store — Wishlist

> Source PRD: `prd/wishlist.md`. The PRD owns the requirements; this plan owns the sequence. Where the two seem to disagree, the PRD's wording is authoritative.

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: a new `wishlist` app under the `wishlist:` namespace, mounted at `""` in the root URLconf like `orders`. It depends on `products` and `accounts` only. Nothing imports it except `dashboard.queries` and the `seed` command — the same one-way rule as `coupons`.
- **URLs**:
  - `/wishlist/`: `wishlist:list`, the signed-in customer's wishlist page
  - `/wishlist/add/<int:pk>/`: `wishlist:add`, POST only, keyed by product pk. It looks the product up among *all* products, not only available ones.
  - `/wishlist/remove/<int:pk>/`: `wishlist:remove`, POST only, keyed by product pk
  - `/wishlist/items/<int:pk>/remove/`: `wishlist:remove_item`, POST only, keyed by wishlist item pk. It fetches the item through the owner's wishlist, never by bare pk.
- **Models**:
  - `Wishlist` is one-to-one with `accounts.User` and is created lazily by a `for_user` class method, as `Cart` is.
  - `WishlistItem` holds a wishlist and a product, unique together, with an `added_at` timestamp. It is listed newest first.
  - The product FK cascades. Nothing is snapshotted, and nothing protects a product from deletion.
  - Saving (get-or-create, so idempotent) and removing (a no-op when the product isn't saved) are model methods on `Wishlist`.
  - Wishlists are not registered in the Django admin.
- **Authorization**: every wishlist view requires sign-in only, with no role checks. Staff have their own wishlists like anyone else. No view exposes another user's wishlist.
- **Rendering**: an inclusion template tag in the wishlist app renders the product-page button, and the add/remove endpoints re-render the same partial. The catalog app's Python never imports the wishlist app, and there is no context processor.

---

## Phase 1: Save a product from its page

**User stories**: 1, 2, 3, 4, 5, 6, 7, 8, 9, 22, 23

### What to build

Create the `wishlist` app with its models and migration, the save and remove model methods, and the two product-pk endpoints (`wishlist:add`, `wishlist:remove`). Add the wishlist button tag and place it beside "Add to cart" on the product detail page, unavailable products included. The button has three states:

- **Signed out**: a plain link to sign-in with a `next` back to the product, labelled "♡ Add to wishlist".
- **Not saved**: an outline "♡ Add to wishlist" button that posts to add.
- **Saved**: a secondary-colored "♥ On your wishlist" button that posts to remove, with a tooltip saying it removes.

The button carries `aria-pressed` for its state. Pressing it swaps only the button via HTMX. Each endpoint performs its one action and re-renders the button, so a repeated add stays saved and a repeated remove stays unsaved.

### Acceptance criteria

- [ ] `Wishlist.for_user` creates a wishlist on first use and returns the same one afterwards
- [ ] Saving a product twice leaves a single item; removing an unsaved product is a no-op
- [ ] An unavailable product can be saved
- [ ] The button renders correctly for signed-out (sign-in link with `next` back to the product), not-saved, and saved, with matching `aria-pressed`
- [ ] The detail page shows the button for both available and unavailable products
- [ ] The add and remove endpoints redirect anonymous visitors to sign-in and refuse GET
- [ ] Add and remove each return the button partial in its new state
- [ ] A staff member can save and remove products like a customer
- [ ] Test suite green, ruff clean

---

## Phase 2: My wishlist page

**User stories**: 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21

### What to build

Add a "Wishlist" link beside "Orders" in the navbar for signed-in users, with no count badge. Build the wishlist page at `wishlist:list`. It extends the base layout and shows a DaisyUI table in an overflow wrapper with a header row. Each row has the product's thumbnail, its name linked to the product page, its price, an availability badge, the existing add-to-cart partial (reused as-is and fed the current cart quantity), and a Remove button. Items are listed most recently saved first. Unavailable products are marked as such and aren't offered for the cart. Adding to the cart leaves the item on the wishlist.

Remove posts to `wishlist:remove_item`, which deletes the item through the owner's wishlist and re-renders the wishlist contents partial without reloading the page, mirroring the cart's line removal. When the list is empty, including right after the last removal, a designed empty state points to the catalog.

### Acceptance criteria

- [ ] The navbar shows "Wishlist" for signed-in users only
- [ ] An anonymous visitor to the wishlist page is redirected to sign-in
- [ ] The page lists only the signed-in user's items, newest first, each with thumbnail, linked name, price, and availability
- [ ] An available product offers add-to-cart; an unavailable product is marked unavailable and isn't offered for the cart
- [ ] Adding a wishlist product to the cart leaves it on the wishlist
- [ ] Removing an item, including an unavailable one, returns the updated contents partial
- [ ] Removing another customer's item is a 404, and their item survives
- [ ] `wishlist:remove_item` redirects anonymous visitors to sign-in and refuses GET
- [ ] The empty state, with its catalog link, appears for an empty wishlist and after the last item is removed
- [ ] Deleting a product removes it from every wishlist
- [ ] Test suite green, ruff clean

---

## Phase 3: Most wishlisted panel and demo wishlists

**User stories**: 24, 25, 26, 27, 28, 29, 30, 31

### What to build

**Query.** Add `most_wishlisted(*, limit: int = 5)` to `dashboard/queries.py`. It returns products annotated with `wishlist_count`, highest first. It counts every wishlist, staff members' included, and includes unavailable products. It deliberately takes no `since` cutoff. Its docstring says it answers "right now", and the module docstring stops claiming that every query takes `since`. Update `docs/ARCHITECTURE.md` if its description of the queries module needs it.

**Panel.** Add a "Most wishlisted" panel to the dashboard, labelled as showing the present. It sits outside the section gated on the store having sales, so it's visible before the first sale, and it ignores the period switcher. Each row has a rank, the product name linked to `products:manage_product_update`, the count, and an "Unavailable" badge when applicable. It never shows customer identities. When nothing is wishlisted, it shows its own empty state.

**Seed and docs.** The `seed` command gives several demo customers wishlists that include at least one unavailable product, so the wishlist pages and the panel have something to show right away. Reset relies on the existing cascades. Add the `wishlist` app to the project layout in CLAUDE.md.

### Acceptance criteria

- [ ] `most_wishlisted` orders products by how many wishlists hold them, highest first, and respects `limit`
- [ ] Unavailable products and staff wishlists are counted
- [ ] Products on no wishlist don't appear
- [ ] The panel shows the same results for every dashboard period
- [ ] The panel renders on a store with no sales and on a store with sales
- [ ] The panel's empty state appears when nothing is wishlisted
- [ ] Each row links to the product's back-office edit page and shows "Unavailable" when applicable
- [ ] The panel shows no customer names or usernames
- [ ] `seed` creates wishlists for several demo customers, including an unavailable product, and running it twice gives the same result
- [ ] CLAUDE.md's project layout lists the `wishlist` app
- [ ] Test suite green, ruff clean
