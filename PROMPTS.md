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
