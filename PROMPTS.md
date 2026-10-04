# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-10-03 — Product images: implemented from the handoff

### Prompts

1. `@HANDOFF.md Implement this feature`
2. *(Interruption)* Rejected my PowerShell command that copied the sample
   images into `products/seed_images/`, then asked: "What does that command
   do?"
3. "Go ahead, and delete the product-images folder once the new copies are
   in place"
4. "How can I manually verify the changes?"
5. *(Follow-up)* "All images load immediately when refreshing the catalog
   page, even ones that are not currently on the screen"
6. The session-log prompt from the top of this file.

### Summary

- **Outcome:** Product images built to the `HANDOFF.md` design.
  - **Model:** `Product.image` (migration `0004`) plus width/height
    columns. `display_image` falls back to the category placeholder.
    `set_image()` shrinks to at most 1200px and saves WebP, keeping
    transparency. `save()`/`delete()` remove replaced, cleared, and deleted
    files.
  - **Form:** `ProductImageField` judges uploads by Pillow's detected
    format and the `MAX_IMAGE_MB = 5` limit, with inline errors. Removal
    is a separate toggle.
  - **Templates:** catalog cards use a fixed 4:3 frame and the detail
    page shows the whole image. The back office gets a list thumbnail
    column and a current-image thumbnail on the form. Images have
    `loading="lazy"` and `width`/`height`.
  - **Seed:** reads `products/seed_images/<slug>.png` and wipes
    `media/products/` first.
  - **Settings:** `MEDIA_ROOT`/`MEDIA_URL`, DEBUG-only media serving, and
    `media/` in `.gitignore`.
  - **Tests:** 16 new tests in `products/test_images.py`. 276 pass and
    ruff is clean. Checked in headless Edge with screenshots of the
    catalog, detail page, back-office list, form, and a rejection.
- **Deviations:**
  - The handoff left the fate of `product-images/` to the user. I meant
    to ask at the end, but the user interrupted the copy command first and
    asked what it did. After my explanation they chose to delete the old
    folder.
  - Departures from the handoff that I chose myself and reported:
    - **Unreadable files:** Pillow can't open HEIC or SVG, so those get
      "isn't an image we can read" rather than the handoff's example
      "is a HEIC file".
    - **MPO:** accepted, because many phone-camera JPEGs come out as MPO.
    - **Upload and remove together:** the upload wins.
    - **Removal UI:** a separate toggle instead of Django's clearable
      widget.
  - The user asked for manual verification steps, then followed up when
    one of those steps didn't hold.
- **Sideways:**
  - **Dimensions bug:** the first test run caught `image_width` staying
    `None`. Django 6 reads dimensions from the content object, and a
    nameless `ContentFile` counts as no file. Naming the content fixed it.
  - **Bad test:** the transparency test used a fully opaque RGBA image,
    whose alpha WebP rightly drops. Fixed the test color, not the code.
  - **Lint:** ruff's DJ012 rejected my method order twice before
    `save`/`get_absolute_url`/`delete` were placed correctly.
  - **Unasked edit:** I rewrote the seed's `tags.set(...)` line for no
    reason and reverted it right away.
  - **Stale CSS:** the first browser pass showed uneven catalog cards.
    `tailwind runserver` had stopped its watcher at once in the
    background, so the CSS was stale (the known trap in memory). There was
    also a real bug: an inline `<a>` kept `h-full` from working. Caught
    from the screenshot, fixed with `block` and a forced Tailwind build.
  - **Database reset:** verifying the seed reset the user's local
    database. I backed up `db.sqlite3` to the scratchpad first and said so.
  - **Wrong verification step:** my manual walkthrough told the user to
    watch lazy loading on desktop, which can't show it. Chromium fetches
    lazy images about 1250px ahead, and a 12-card desktop page fits inside
    that. Measured it to confirm: desktop loaded 10 of 10 distinct images
    up front, phone width loaded 4 and more on scroll. Corrected the steps
    to use DevTools device mode. No code change.

## 2026-10-03 — Product images: grill-me design interview and handoff

### Prompts

1. `/grill-me Each product in the catalog should have an image associated
   with it. If an image has not been uploaded for a product, the placeholder
   image should be displayed. Employees should be able to add product images
   via the back office page. If an employee uploads an incompatible file, the
   upload should be rejected and an explanation given to the user.`
2. "Keep per-category": Q1, an uploaded image falls back to the existing
   category placeholder.
3. "Exactly one": Q2, one optional `ImageField` on `Product`, no gallery.
4. "On the product form": Q3, the upload goes on the existing create/edit
   `ProductForm`.
5. "JPEG, PNG, WebP": Q4, the allowed formats.
6. "5 MB": Q5, the maximum upload size.
7. *(Clarification)* Declined to answer Q6 (store as-is / downscale /
   thumbnails), then asked: "A requirement that I did not mention is that
   pages should load fast. Does this requirement change your
   recommendation?"
8. "Downscale + WebP": Q6 re-asked, shrink to at most 1200px and re-encode
   as WebP on save.
9. "Clear + delete old files": Q7, the image lifecycle.
10. "Yes, seed attaches them": Q8, `seed` attaches the sample images from
    `product-images/`.
11. "SoulSear Mark II" and "No Text version": Q9, resolving the two
    ambiguous filenames.
12. "+ back-office thumbnails": Q10, where images display.
13. *(Correction)* "Do not write this up anywhere": no PRD or plan.
14. `/handoff the next session implements the design we just agreed`
15. The session-log prompt from the top of this file.

### Summary

- **Outcome:** A ten-question design interview for product images, then a
  handoff. No feature code was written. The agreed design and the
  file-to-product image mapping are in `HANDOFF.md` for the next session to
  implement. The working tree is otherwise as the session found it: the
  uncommitted Pillow dependency, the untracked `product-images/`, and the
  trailing-newline change in `config/urls.py`.
- **Deviations:**
  - Every answer took my recommendation, but Q6 only after a follow-up.
    The user brought in a requirement they hadn't stated, that pages load
    fast. That flipped my recommendation from "store as-is" to "downscale +
    WebP", plus `loading="lazy"` and width/height attributes.
  - When I offered a PRD and plan, the user declined.
- **Sideways:**
  - My first Q6 recommendation (store as-is) was built on the stated
    requirements only. I never asked about performance, even though I had
    already seen that the sample images are about 2 MB each and the catalog
    shows 12 per page. The user caught it.
  - "Do not write this up anywhere" (prompt 13) and `/handoff` (prompt 14)
    pulled in opposite directions. I treated the explicit `/handoff` as the
    exception and wrote `HANDOFF.md`, flagged it in my reply, and offered to
    delete it.

## 2026-09-26 — Dollar-off item coupons apply per unit: grill-me, then the fix

### Prompts

1. `/grill-me Item specific coupons with a set dollar discount should apply to
   each of that item that is purchased, not just the first`
2. "A" — Q1, change the meaning for every dollar-off item coupon as a bug
   fix, with no new field or kind.
3. "A" — Q2, no limit on discounted units; the line total is the only cap.
4. "C" — Q3, add "each" to `Coupon.summary` and explain the rule in the
   `value` help text.
5. "A" — Q4, `amount_off(base, *, units=1)`.
6. "A" — Q5, update the four assertions that expected the old amount and add
   focused tests.
7. *(Correction)* "Go ahead, but do not add the entry to PROMPTS.md - I will
   ask you to do that manually"
8. "How can I verify this feature manually?"
9. The session-log prompt from the top of this file.

### Summary

- **Outcome:** A five-question design interview, then the fix. A
  dollar-off item coupon now takes its value off each unit in the line:
  `min(value × units, line total)`. `Coupon.amount_off` gained a
  keyword-only `units=1`. `discount_for` passes the line's quantity, and so
  does the seed's `_build_order`. Percent coupons and order-wide coupons are
  unchanged. `Coupon.summary` now reads "$25.00 off each Seraphine Home Hub".
  The `value` help text explains the rule, which needed migration
  `coupons/0002_value_help_text_per_unit` (help text only). The coupons
  module docstring and the CLAUDE.md coupons line were also updated. Tests:
  four assertions went from $25 to $50 (the shared `cart_item` fixture holds
  2 Hubs), the summary assertion now expects "each", and four tests were
  added (units=3, the cap with units, percent ignores units, a single unit
  takes $25). The suite went from 255 to 259, green, and ruff is clean. Left
  **uncommitted on `main`**.
- **Deviations:** None on the design; all five answers took my
  recommendation. One correction: my plan listed writing this PROMPTS.md
  entry as a build step, which breaks this file's rule that entries come
  only from the session-log prompt. The user struck it before I started. One
  follow-up question came after the build: how to verify it by hand.
- **Sideways:**
  - Exploring the code before Q5 showed that `cart_item` has quantity 2, so
    the existing tests had locked in the one-time $25 behavior. That became
    Q5 rather than a surprise failure mid-build.
  - My first draft of the `amount_off` docstring said order-wide coupons
    "ignore" `units`. That was wrong, because a dollar amount would multiply.
    I fixed it before running anything: order-wide callers leave it at 1.
  - The first `pytest` run took about 119s and passed the 120s tool timeout,
    so it finished in the background.
  - `ruff format --check` flagged a test signature I had wrapped by hand. I
    fixed it with Edit, not with `ruff format`, and ruff then came back
    clean. The suite wasn't re-run after that change, which only joined one
    line.
  - The seed change has no test coverage, because tests never invoke the
    seed. The seeded SERAPHINE25 still has zero uses, so no seeded order
    exercises the change either.
  - The manual checklist can't hit the cap with SERAPHINE25, because a Hub
    costs far more than $25. Testing the cap means creating a coupon worth
    more than its product's price. The user has not yet reported back on the
    checklist.

## 2026-09-26 — Coupon codes: grill-me design interview, then the build

### Prompts

1. `/grill-me I want to add a coupon feature - customers can enter seasonal
   coupon codes at checkout. Some coupons apply to entire orders and some are
   specific to a single item. The marketing team should be able to create and
   retire codes on their own.`
2. "Let's add both options" — Q1, discount kind (recommended: percentage only).
3. "Cap plus optional minimum spend" — Q2, discount larger than its base.
4. "Apply the discount to the whole line. Each item coupon targets exactly one
   product." — Q3, what an item coupon discounts.
5. "The cart subtotal" — Q4, what minimum spend measures.
6. "One coupon per order" — Q5, stacking.
7. "Option 1 is good" — Q6, `Order.total` is the amount charged, plus snapshot
   fields.
8. "Let's go with Option 2" — Q7, item discounts also recorded on the line.
9. "Option 3 - do not delete coupons, having the history is desirable" — Q8,
   `is_active` switch plus optional date window.
10. "Option 2" — Q9, once per customer, counted from non-cancelled orders.
11. "Option 1" — Q10, any staff member manages coupons.
12. "Option 2" — Q11, checkout field plus HTMX Apply preview.
13. "Option 1" — Q12, block the order and show the error on the form.
14. "Option 2" — Q13, terms lock once used; schedule stays editable.
15. "Option 2" — Q14, per-coupon usage numbers on the Coupons tab.
16. "Option 2" — Q15, a new `coupons` app.
17. "Option 1, America/Chicago is the right timezone" — Q16, inclusive date
    fields judged in store-local time.
18. "Option 3" — Q17, skip the PRD/plan docs and start building
    (recommended: write them first).
19. *(Correction)* Rejected a `uv run python` script that rewrote
    `orders/services.py`, then: "Please explain the command you are asking to
    run"
20. "Make the change using Edit"
21. "Option 2" — Q18, raised mid-build: keep `clean_coupon_code` and relax the
    checkout form's declarative-only test (recommended: drop it).
22. "How can I manually verify this feature in the browser?"
23. "The phone layout did not work - the summary and coupon box appreared below
    the place order button"
24. *(Correction)* Declined installing the Claude in Chrome extension when I
    reached for it to check the layout.
25. "The hard refresh fixed it"
26. "I don't want a coupons branch - everything should be on the main branch"
27. "No, don't commit - I will do that myself"
28. "Stop the dev server"
29. The session-log prompt from the top of this file.

### Summary

- **Outcome:** An 18-question design interview, then a full build. New
  `coupons` app: `Coupon` (percent or fixed amount; whole order or one
  `Product`; optional minimum spend against the cart subtotal; `is_active`
  plus an optional inclusive `starts_on`/`ends_on` window; retired, never
  deleted) with every rule in `Coupon.discount_for`, raising `CouponError`
  (a `ValueError`) with a customer-facing reason. `place_order`'s dormant
  `coupon_code` seam is now live and re-checks the code inside its
  transaction. `Order` gained `discount`, `coupon` (PROTECT) and
  `coupon_code`, and `total` is now the amount charged; `OrderItem` gained
  `discount`, and `top_products` subtracts it. Checkout has an HTMX Apply
  preview in the order summary; only an applied code rides into the form via
  a hidden input. Back office has a Coupons tab (status, uses, total
  discounted), a per-coupon page listing its orders, create/edit with terms
  locked after first use, and Retire/Reactivate. `TIME_ZONE` is now
  `America/Chicago` (env-overridable). The seed adds a `marketing` /
  `marketing123` staff login and six coupons, one per status. README and
  CLAUDE.md updated. Suite went from 196 to 255, green; ruff clean. Left
  **uncommitted on `main`** at the user's request.
- **Deviations:** Three answers went against my recommendation. Q1: both
  percent and fixed amounts, not percent only. Q17: skip the PRD/plan docs
  and build straight away, so `prd/core-platform.md:86` still says the
  checkout form has "no `clean_*` methods" and that a valid form always
  becomes an order; both are now untrue. Q18: keep `clean_coupon_code` and
  narrow the test to allow that one exception. The user rejected one tool
  call and asked what it did before letting the change go ahead through
  Edit. Two follow-up questions came after the build: how to verify in a
  browser, and a layout bug report. I made one design deviation of my own,
  without asking first: `Order.subtotal` is a derived property
  (`total + discount`) rather than the stored column agreed in Q6. I
  disclosed it afterwards, and it was not revisited.
- **Sideways:**
  - I rewrote `orders/services.py` with a find-and-replace script instead of
    Edit, which hid the diff. The user rejected it, and I redid it with Edit.
  - Q12's `clean_coupon_code` broke an existing PRD-contract test
    (`test_the_form_declares_no_imperative_validation`). I should have found
    that test while exploring, before recommending the approach. It surfaced
    only when the suite ran, which forced Q18 mid-build.
  - The seed smoke test on a scratch DB caught two bugs the unit tests
    missed. The Coupons list was unordered, because `Meta.ordering` is
    dropped from `GROUP BY` queries. SQLite also returned discount sums at
    float precision (`51.6000000000000`). Both were fixed, and a test was
    added for the ordering.
  - I cleaned up a sloppy test helper and a whitespace-dependent assertion
    before finishing.
  - The "phone layout didn't work" report was not a code bug. The compiled
    CSS and the HTML were correct; the browser had reused a cached
    `tailwind.css` (unversioned URL, no Cache-Control), and a hard refresh
    fixed it.
  - I created a `coupons` feature branch without asking, and the user wanted
    everything on `main`. Nothing had been committed, so switching was clean.
    `git log coupons` failed on the first try because the name also matches
    the `coupons/` directory.
  - In the seed data, SERAPHINE25 has zero uses, so no seeded order line
    carries an item discount.
  - The user confirmed only the phone-layout step of the manual checklist;
    the rest has not been reported on.
  - I saved three memories for future sessions: the stale-CSS hard refresh,
    Edit-only file changes, and main-only with the user doing commits.

## 2026-09-18 — `Product.is_featured` and the Featured badge

### Prompts

1. "Add an is_featured field to the Product model. This field should be a
   boolean and should default to false. Existing products should be
   unfeatured."
2. "What does the recommended test do?" — asked after interrupting and
   rejecting the `uv run pytest` call, before allowing it.
3. "Run it, please."
4. "Add a \"Featured\" badge that displays when a product is featured. The
   badge should display next to the product name on both the catalog and the
   product's detail page."
5. "Can you change the color of the badge in order to differentiate it from
   the \"Add to Cart\" button?"
6. The session-log prompt from the top of this file.

### Summary

- **Outcome:** Added `is_featured = BooleanField(default=False)` to `Product`
  (`products/models.py:68`) with migration `0003_product_is_featured`, applied;
  `default=False` backfills existing rows, so every current product is
  unfeatured as asked. Added a "Featured" badge beside the product name in
  `templates/products/catalog.html` (inside the flex `card-title`, `badge-sm`)
  and `templates/products/detail.html` (the bare `<h1>` needed wrapping in a
  `flex flex-wrap items-center gap-3` div). Badge color ended at
  `badge-accent`. Suite green at 164 tests after each change.
- **Deviations:** Two. The test run was interrupted and questioned before
  being approved on the second ask — nothing about the run changed, the
  question was about what it covered. The badge color was my choice of
  `badge-primary`, which collided with the `btn-primary` Add to cart button;
  the user asked for differentiation and it became `badge-accent`. That
  collision was avoidable — the button sits directly below the badge on the
  catalog card and I had the partial open.
- **Sideways:** I answered the "what does the test do" question with a test
  count of 79, taken from grepping `def test` lines; the actual run reported
  164 because parametrized tests expand. Caught by the run itself and
  corrected in the next message. Also worth flagging for the next session:
  no product has `is_featured=True` yet, so **the badge has never actually
  been seen rendering** — it is verified only by the suite passing, not by
  eye. And `badge-accent` is a class new to this codebase, so
  `manage.py tailwind build` must run before any deploy or it will be absent
  from the compiled CSS. The back-office product form does not expose
  `is_featured`, so the flag is currently settable only from the shell or a
  seed; this was raised and not picked up.
