# Plan: The ThoughtTronix Store — Customer Reviews

> Source PRD: `prd/reviews.md`. The PRD owns the requirements; this plan owns the sequence. Where the two seem to disagree, the PRD's wording is authoritative.

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: a new `reviews` app under the `reviews:` namespace, mounted at `""` in the root URLconf like `wishlist`. It depends on `products`, `orders`, and `accounts`; dependencies point one way. The catalog app's Python never imports it: the product page gets its reviews section through an inclusion template tag, and the catalog's star annotation uses the reverse relation by name. Only the `seed` command imports it from outside.
- **URLs**:
  - `/reviews/add/<int:pk>/`: `reviews:create`, POST only, keyed by product pk. It looks the product up among *all* products, so a product that is no longer sold can still be reviewed.
  - `/reviews/<int:pk>/edit/`: `reviews:edit`, keyed by review pk. GET returns the edit form partial; POST saves and returns the updated review partial, or the form with errors.
  - `/reviews/<int:pk>/cancel/`: `reviews:cancel`, GET, returns the unchanged review partial.
  - `/reviews/<int:pk>/delete/`: `reviews:delete`, POST only.
  - `/backoffice/reviews/`: `reviews:manage_reviews`, staff only, with an optional `?rating=` filter (1–5; anything else is ignored).
- **Models**:
  - `Review`: an author (FK to `accounts.User`), a product (FK to `products.Product`), a rating, a comment, `created_at`, and `updated_at`. Both FKs cascade and both use `related_name="reviews"`.
  - Author and product are unique together, enforced by a database constraint.
  - The rating is a small positive integer validated to 1–5. The comment is required, capped at 2,000 characters, and whitespace-only counts as blank.
  - `created_at` defaults to now (no auto-now-add, as with orders, so the seed can backdate). `updated_at` changes on every save.
  - A property reports whether the review was edited, with a small tolerance so creation itself never counts.
  - Ordering is newest first. Nothing is snapshotted.
  - A custom queryset/manager on `Review` owns **eligibility to create** (signed in, not staff, at least one non-cancelled order containing the product, not already reviewed), **may still edit** (the same purchase check without the "not already reviewed" part), and **the summary** (average rating and count for a product). Views, the inclusion tag, and the seed all call these.
  - `accounts.User` gains a public-name property: first name and last initial ("Nova K."), falling back to the username when the name is blank.
- **Authorization**:
  - Every review view requires sign-in. Every state-changing endpoint is POST only.
  - Customers look reviews up **through their own reviews**, never by bare pk, so another customer's review is a 404. Staff look reviews up among all reviews.
  - Staff are always moderators, never owners. They never create, skip the purchase check, and always get the comment-only form, so the rating is not a field at all.
  - Create and customer edit re-check their rules on the server and refuse with a 403 when the rule fails, changing nothing.
- **Rendering**:
  - The same views serve the product page and the back office. The request names the surface it came from, and the view renders the matching partial (a review card or a back-office row).
  - The product page's "Your review" slot is one stable HTMX target for every customer action.
  - Every create, customer edit, and delete response on the product page also refreshes the summary with an out-of-band swap. Back-office responses don't include it.
  - The rating input is DaisyUI's `rating` component (radio inputs), with no JavaScript. Delete uses `hx-confirm` on both surfaces.

---

## Phase 1: Read reviews on the product page

**User stories**: 1, 2, 4, 5, 10, 11, 19, 21, 23, 24, 25, 35, 38

### What to build

Create the `reviews` app with the `Review` model and migration, its queryset rules, the "(edited)" property, and the public-name property on `User`. Add the reviews-section inclusion tag and place it below the product details on the detail page, for available and unavailable products alike. The section has three parts:

- **Summary**: the average as read-only stars and a number to one decimal, plus the count. A product with no reviews says so.
- **"Your review" slot**, by viewer:
  - signed out: "Sign in to review", linking to sign-in with a `next` back to the product;
  - signed-in customer who hasn't bought the product: "Only customers who bought this product can review it";
  - customer who has already reviewed it: their own review card, with no actions yet;
  - eligible customer: left as a placeholder for the form in Phase 2;
  - staff: nothing.
- **List**: everyone else's reviews, newest first, unpaginated. Each card shows stars, the comment, the public name, the date, and "(edited)" when applicable. The viewer's own review is not repeated here. A staff member who once reviewed as a customer sees their review in the list, since staff have no slot.

### Acceptance criteria

- [ ] Eligibility allows placed, shipped, and delivered orders and refuses when the only order is cancelled
- [ ] Eligibility refuses anonymous users, staff, and a customer who has already reviewed the product
- [ ] Eligibility allows a product that is no longer available
- [ ] May-still-edit follows the same purchase check, ignoring the existing review
- [ ] A second review by the same author of the same product is rejected by the database
- [ ] The summary gives the right average and count, and the empty case reads "no reviews"
- [ ] The "(edited)" property is false for a fresh review and true after a meaningfully later save
- [ ] The public name is "First L." and falls back to the username when the name is blank
- [ ] The "Your review" slot renders correctly for a visitor (with `next`), a non-buyer, an existing reviewer, and staff
- [ ] The list is newest first and excludes the viewer's own review
- [ ] A review stays up after the order behind it is cancelled
- [ ] Deleting a product or a user deletes their reviews
- [ ] Test suite green, ruff clean

---

## Phase 2: Write a review, catalog stars, and demo reviews

**User stories**: 3, 6, 7, 8, 9, 12, 18, 20, 36, 37

### What to build

**Writing.** Add the customer review form (rating and comment; the form owns range and length validation) and place it in the "Your review" slot for eligible customers, with the DaisyUI star-rating input. Submitting posts to `reviews:create` via HTMX. The view re-checks eligibility on the server and refuses an ineligible request without creating anything. On success it re-renders the slot, now showing the new review, and refreshes the summary out-of-band. An invalid form re-renders the slot with the form and its errors in place.

**Catalog stars.** Annotate the catalog queryset (which the category view inherits) with each product's average rating and review count through the `reviews` reverse relation. Product cards show the stars and count, and a product with no reviews shows no stars. There is no query per card.

**Seed.** Extend the `seed` command to create reviews for roughly half of the eligible customer–product pairs among the demo world's non-cancelled orders. It uses the existing seeded random generator, with ratings skewed toward 4 and 5 and a few hand-written comments for the named demo customers. Eligibility comes from the same model-layer rule the views use. The seed never reviews as staff and never creates two reviews of one product by the same customer. Backdate every review to after its order. Set `created_at` and `updated_at` together without going through a normal save, so backdated reviews don't show "(edited)". Leave at least one named demo customer with an eligible purchase they haven't reviewed, so the form can be demoed right after a reset. Reset relies on the existing cascades.

**Docs.** Add the `reviews` app and its one-way import rule to the project layout in CLAUDE.md.

### Acceptance criteria

- [ ] An eligible customer sees the form in the slot
- [ ] A valid submission creates the review and returns the slot showing it, plus an out-of-band summary with the new average and count
- [ ] A missing rating, an out-of-range rating, a blank or whitespace-only comment, and a comment over 2,000 characters each re-render the form with an error and create nothing
- [ ] An ineligible customer (no qualifying order, or already reviewed) is refused and nothing is created
- [ ] Staff are refused and nothing is created
- [ ] A customer can review a product right after placing the order, and can review an unavailable product they bought
- [ ] `reviews:create` redirects anonymous visitors to sign-in and refuses GET
- [ ] Catalog and category cards show the average and count, and products with no reviews show no stars
- [ ] `seed` creates reviews, none by staff, none duplicating a customer–product pair, and each backed by a non-cancelled order for its product
- [ ] Every seeded review is dated after an order containing its product, and none reports as edited
- [ ] At least one named demo customer still has an eligible, unreviewed purchase
- [ ] Running `seed` twice gives the same result
- [ ] CLAUDE.md's project layout lists the `reviews` app and its import rule
- [ ] Test suite green, ruff clean

---

## Phase 3: Customers edit and delete their own review

**User stories**: 13, 14, 15, 16, 17, 18, 22

### What to build

Give the customer's own review card in the slot **Edit** and **Delete**. Edit GETs `reviews:edit`, which swaps the card for the form pre-filled with rating and comment. Saving POSTs to the same URL and returns the updated card, or the form with errors. Cancel GETs `reviews:cancel` and returns the card unchanged. Editing requires a non-cancelled order for the product; without one, the request is refused.

Delete asks for confirmation with `hx-confirm`, then POSTs to `reviews:delete`. It is always allowed for the owner, and the slot falls back to the form if the customer still qualifies, or the non-buyer message if not. Every save and delete refreshes the summary out-of-band. All lookups go through the customer's own reviews.

### Acceptance criteria

- [ ] Edit returns the pre-filled form, and save returns the updated card with "(edited)" and an out-of-band summary
- [ ] An invalid save returns the form with errors and leaves the review unchanged
- [ ] Cancel returns the card unchanged
- [ ] Delete removes the review, returns the form for a customer who still qualifies, and refreshes the summary
- [ ] An owner whose only order was cancelled can delete (the slot then shows the non-buyer message) but cannot edit
- [ ] Another customer's review is a 404 for edit, cancel, and delete, and survives
- [ ] Save and delete redirect anonymous visitors to sign-in and refuse GET
- [ ] Test suite green, ruff clean

---

## Phase 4: Staff moderate on the product page

**User stories**: 26, 27, 28

### What to build

Add the staff moderation form, which has only the comment field. For staff, every review card in the list shows **Edit** and **Delete**, served by the same `reviews:edit`, `reviews:cancel`, and `reviews:delete` views. Staff look reviews up among all reviews, skip the purchase check, and always get the comment-only form, so a submitted rating is ignored. Edit swaps only the card that was clicked. Delete confirms first, returns nothing so the card disappears, and refreshes the summary out-of-band. A staff member who once reviewed as a customer moderates that review the same way.

### Acceptance criteria

- [ ] Staff see Edit and Delete on every review card, and customers see them on no one else's
- [ ] A staff edit gets the comment-only form, and saving changes the comment while a submitted rating is ignored
- [ ] A staff edit works on a review whose author no longer has a qualifying order
- [ ] A staff delete removes the review, returns an empty card, and refreshes the summary
- [ ] A staff member's own earlier customer review gets the comment-only form
- [ ] Test suite green, ruff clean

---

## Phase 5: Back-office Reviews tab

**User stories**: 29, 30, 31, 32, 33, 34

### What to build

Add a **Reviews** tab to the staff shell's tab rail with its own `section` name, and the `reviews:manage_reviews` list view: all reviews, newest first, 20 per page, with the `?rating=` filter shaped like the Orders tab's status filter. It's a DaisyUI table in an overflow wrapper with a header row. Each row partial shows the product (linked to its public page), the reviewer's full name and username, the stars, the comment, the date, and Edit and Delete.

Edit and Delete reuse the Phase 4 views. The request names the back-office surface, so they render the row partial instead of a card and include no summary. Edit swaps the row for an inline comment-only form, and save and cancel return the row. Delete confirms, then removes the row in place without re-fetching the page. Rows on later pages behave the same. A designed empty state covers both no reviews at all and a filter that matches nothing.

### Acceptance criteria

- [ ] The tab appears in the rail and is active on the Reviews page
- [ ] Customers and anonymous visitors cannot reach the page
- [ ] Reviews are listed newest first, 20 per page
- [ ] `?rating=1` through `?rating=5` filter the list, and any other value is ignored
- [ ] Each row shows the product link, full name, username, stars, comment, and date
- [ ] Back-office edit, save, and cancel return the row partial with no out-of-band summary, and a submitted rating is ignored
- [ ] Back-office delete removes the review and returns empty content
- [ ] The empty state appears for no reviews and for a filter that matches nothing
- [ ] Test suite green, ruff clean
