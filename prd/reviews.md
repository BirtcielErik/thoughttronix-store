# PRD: The ThoughtTronix Store — Customer Reviews

*Commissioned by ThoughtTronix Product Management. "Your Thoughts, Our Business."*

---

## Problem Statement

A ThoughtTronix shopper deciding whether to buy a product has only the store's own word to go on: the name, the tagline, the description, and the price. There is no way to learn what people who actually bought the product thought of it, so every purchase is a leap of faith, and a shopper comparing two products in the catalog has nothing to tell them apart but marketing copy.

Customers who have bought something have the mirror-image problem. They have an opinion — delighted or disappointed — and nowhere to put it.

The store has a problem too. Without reviews it cannot see how customers feel about what it sells, and if it simply opened a comment box, it would invite reviews from people who never bought the product, multiple reviews from one person, and content no one can moderate.

## Solution

**Customer reviews**, written only by verified buyers and moderated by staff.

**One review per product, from people who bought it.** A customer who has at least one order containing a product — any order that has not been cancelled — can leave one review of that product: a star rating from 1 to 5 and a written comment. Staff cannot write reviews, so every review on the site means the same thing: "a customer who bought this."

**Reviews on the product page.** Below a product's details is a reviews section:

- A **summary** — the average rating as stars and a number, and how many reviews there are.
- A pinned **"Your review"** slot at the top of the list. What it shows depends on who is looking:
  - a customer who bought the product and has not reviewed it sees the review form;
  - a customer who has already reviewed it sees their own review, with **Edit** and **Delete**;
  - a signed-in customer who has not bought it sees "Only customers who bought this product can review it";
  - a visitor who is not signed in sees "Sign in to review", which brings them back to the product afterwards;
  - staff see nothing here.
- **Everyone else's reviews**, newest first, each showing the stars, the comment, the reviewer's first name and last initial (for example "Nova K."), the date, and "(edited)" if it has been changed since it was posted.

Creating, editing, and deleting a review all happen without reloading the page. Editing swaps the review for a pre-filled form right where it sits; saving puts the updated review back, and cancelling restores it unchanged. Deleting asks "Are you sure?" first. Every change that affects the numbers updates the summary at the same time.

**Customers manage their own reviews.** A customer can edit their review's rating and comment, or delete it. To edit, they must still have a non-cancelled order for the product; anyone can always delete their own review. A review stays up if the order behind it is later cancelled.

**Stars in the catalog.** Every product card in the catalog and category pages shows the product's average rating and review count, so shoppers can compare while browsing.

**Staff moderate.** Staff can edit and delete any review — but they can edit only the comment, never the rating. Moderation means removing harmful text, not changing a customer's opinion; a review whose rating is illegitimate is deleted, not rewritten. Staff do this in two places:

- on the **product page**, where every review card shows staff **Edit** and **Delete**;
- on a new **Reviews** tab in the back office: every review on the site, newest first, 20 per page, filterable by star rating so staff can go straight to the 1-star reviews. Each row shows the product, the reviewer's full name and username, the stars, the comment, and the date, with inline **Edit** and **Delete** that also work without reloading the page.

**Demo data.** Resetting the store to the demo world also creates a realistic set of reviews — for some, but deliberately not all, of the demo customers' real purchases — so the catalog stars, the product summaries, and the moderation tab have something to show from the start, and at least one demo customer still has a purchase waiting to be reviewed.

## User Stories

**Visitor (not signed in)**

1. As a visitor, I want to read a product's reviews, so that I can learn what buyers think before I buy.
2. As a visitor, I want to see a product's average rating and review count on its page, so that I can judge it at a glance.
3. As a visitor, I want to see each product's average rating and review count on the catalog and category pages, so that I can compare products while browsing.
4. As a visitor, I want a "Sign in to review" link where the review form would be, so that I know I can review a product once I sign in.
5. As a visitor, I want signing in from that link to bring me back to the same product, so that I do not have to find it again.

**Customer (signed in)**

6. As a customer who bought a product, I want to leave a review with a star rating from 1 to 5 and a written comment, so that I can share my experience with other shoppers.
7. As a customer, I want to be able to review a product as soon as I have placed an order for it, so that I do not have to wait for delivery to share my opinion.
8. As a customer, I want my review to appear on the page without a reload when I submit it, so that I do not lose my place.
9. As a customer, I want the form to tell me what is wrong, in place, if I leave out the rating or the comment or write too much, so that I can fix it without starting over.
10. As a customer, I want my own review pinned at the top of the reviews, so that I can always find it.
11. As a customer, I want to be told plainly when I cannot review a product because I have not bought it, so that I understand why there is no form.
12. As a customer, I want to be prevented from reviewing the same product twice, so that my opinion counts once, like everyone else's.
13. As a customer, I want to edit my review's rating and comment in place, so that I can update my opinion after using the product longer.
14. As a customer, I want to cancel an edit and get my review back unchanged, so that I can back out of a change.
15. As a customer, I want to delete my review, with a confirmation first, so that I can take it down without deleting it by accident.
16. As a customer, I want to always be able to delete my own review, even if I no longer have a qualifying order, so that I am never stuck with something I wrote.
17. As a customer who deleted my review, I want the review form to come back if I still qualify, so that I can write a new one.
18. As a customer, I want the summary at the top of the reviews to update when I add, change, or delete my review, so that the numbers always match what I see.
19. As a customer, I want my review to stay up even if one of my orders is later cancelled, so that my writing does not vanish without explanation.
20. As a customer, I want to be able to review a product I bought even after the store stops selling it, so that my purchase still counts.
21. As a customer, I want my review shown under my first name and last initial, so that my full name is not published.
22. As a customer, I want no other customer to be able to edit or delete my review, so that my words stay mine.
23. As a shopper, I want reviews labelled "(edited)" when they have been changed after posting, so that I know the text is not exactly what was first written.
24. As a shopper, I want reviews shown newest first, so that I see the most current opinions.

**Employee (staff)**

25. As an employee, I want no review form on product pages, so that reviews only ever come from customers and never from the store's own staff.
26. As an employee, I want Edit and Delete on every review when I view a product page, so that I can moderate a problem review the moment I see it.
27. As an employee, I want my Edit to change only the comment, never the rating, so that I can remove harmful text without altering a customer's opinion.
28. As an employee, I want to delete any review, with a confirmation first, so that I can remove fake or abusive reviews without deleting one by accident.
29. As an employee, I want a Reviews tab in the back office listing every review, newest first, so that I can see what has been posted without visiting products one by one.
30. As an employee, I want to filter the Reviews tab by star rating, so that I can go straight to the reviews most likely to need attention.
31. As an employee, I want the Reviews tab paginated, so that it stays usable as reviews accumulate.
32. As an employee, I want each row to show the product, the reviewer's full name and username, the stars, the comment, and the date, so that I know exactly who wrote what about what.
33. As an employee, I want to edit a comment and delete a review right in the Reviews tab without the page reloading, so that moderating many reviews is quick.
34. As an employee, I want a designed empty state on the Reviews tab, including when a rating filter matches nothing, so that an empty list does not look broken.
35. As an employee, I want deleting a product to remove its reviews with it, so that no reviews are left pointing at nothing.

**Developer**

36. As a developer, I want resetting the demo world to create reviews that obey every review rule, so that the demo never shows a state the app forbids.
37. As a developer, I want the demo world to leave at least one demo customer with a purchase they have not reviewed, so that I can demonstrate the review form immediately.
38. As a developer, I want "one review per customer per product" enforced by the database, so that a double-click or a race can never create two reviews.

## Implementation Decisions

**A new `reviews` app.** The feature lives in its own app, with its own `reviews` URL namespace and templates. It depends on the catalog, orders, and accounts; dependencies point one way. The catalog app's Python never imports it: the product page gets its reviews section through an inclusion template tag, as it gets the wishlist button, and the catalog's star annotation uses the reverse relation by name. Only the seed command imports the reviews app from outside it.

**Model.**
- `Review` — an author (the user), a product, a rating, a comment, `created_at`, and `updated_at`.
- A unique constraint on author and product enforces one review per customer per product in the database, not only in the form.
- The rating is a small positive integer validated to the range 1–5.
- The comment is required and capped at 2,000 characters; whitespace-only counts as blank.
- `created_at` uses a default of "now" rather than auto-now-add, as orders do, so the seed can backdate reviews. `updated_at` updates on every save; the seed therefore sets both timestamps together without going through a normal save, so backdated reviews do not look freshly edited.
- A model property reports whether the review was edited (updated meaningfully later than created, with a small tolerance so creation itself never counts), driving the "(edited)" label.
- Both the product and the author relations cascade. A review only has meaning on its product's page, so unlike order lines nothing is snapshotted and nothing protects the product from deletion; a product that should keep its reviews is marked unavailable instead, and its page still shows them.
- Ordering is newest first.

**The rules live in the model layer.** A custom queryset/manager on `Review` owns:
- **eligibility** — whether a user may create a review of a product: signed in, not staff, has at least one order containing the product that is not cancelled, and has not already reviewed it. "Purchased" deliberately means the same as everywhere else in the codebase: every status except cancelled, which is how the dashboard already counts sales;
- **whether a user may still edit** their review — the same purchase check, without the "not already reviewed" part;
- **the summary** — average rating and count for a product.

The views, the inclusion tag, and the seed all call these, so each rule is defined once.

**Forms.** A customer review form with rating and comment. A staff moderation form with the comment only — the rating is not a field at all, so it cannot be changed even by a crafted request. Forms own the length and range validation.

**Who may do what.**
| Action | Customer (owner) | Customer (not owner) | Staff | Visitor |
|---|---|---|---|---|
| Create | if eligible | — | never | — (sign-in link) |
| Edit rating | if still has a qualifying order | no | never | no |
| Edit comment | if still has a qualifying order | no | always | no |
| Delete | always | no | always | no |

Staff are always moderators, never owners: staff actions skip the purchase check, and a staff user always gets the comment-only form.

**URLs and views.** All review views are thin class-based views requiring sign-in; every state-changing endpoint is POST-only.
- **Create** is keyed by product. It re-checks eligibility on the server whatever the page showed, and refuses an ineligible request without creating anything. On success it renders the "Your review" slot (now showing the review). An invalid form re-renders the slot with the form and its errors.
- **Edit form**, **save**, and **cancel** for a review: a GET returns the edit form partial in place of the review; save returns the updated review partial, or the form with errors; cancel returns the unchanged review partial.
- **Delete** removes the review and returns the replacement content: on the product page, the "Your review" slot (the form again if the customer still qualifies, otherwise the non-buyer message) for an owner, or nothing for a staff deletion from the list; in the back office, nothing, so the row disappears.
- A customer's edit and delete look the review up **through their own reviews**, never by bare pk, so another customer's review is a 404 — the same pattern as removing a wishlist item. Staff look reviews up among all reviews.
- The same views serve the product page and the back office. The request says which surface it came from, and the view renders the matching partial (a review card or a back-office row); only the templates differ.

**The product page reviews section.** Rendered by an inclusion tag from the reviews app, so the first render and every HTMX update use the same partials.
- The **summary** shows the average as read-only stars and a number to one decimal, plus the count; a product with no reviews says so.
- The **"Your review" slot** is a single, stable HTMX target for every customer action, so a new review never has to be inserted into the middle of the list. The viewer's own review appears there and is not repeated in the list below.
- The **list** shows all other reviews, newest first, unpaginated, each as one review-card partial reused for the initial render and after every action. Staff Edit swaps only the card that was clicked.
- Every create, customer edit, and delete response on the product page also refreshes the summary with an **out-of-band swap**, following the cart badge and checkout summary precedent. Back-office responses do not include it.
- The rating input uses DaisyUI's `rating` component (radio inputs styled as stars), so it needs no JavaScript.
- Delete uses `hx-confirm`, HTMX's built-in confirmation, on both surfaces.
- The reviewer's public name comes from a property on the user: first name and last initial, falling back to the username when the name is blank.

**Catalog cards.** The catalog's queryset — which the category view inherits — is annotated with each product's average rating and review count, so the cards show stars without a query per card. A product with no reviews shows no stars.

**The back-office Reviews tab.** A new tab in the staff shell's tab rail, with its own section name.
- A list view of all reviews, newest first, 20 per page, with an optional rating filter in the querystring (1–5; anything else is ignored), in the same shape as the Orders tab's status filter.
- A DaisyUI table in an overflow wrapper with a header row, per the frontend conventions. Each row is a row partial showing the product (linked to its public page), the reviewer's full name and username, the stars, the comment, the date, and Edit and Delete.
- Edit swaps the row for an inline comment-only form; save and cancel return the row. Delete removes the row in place. Rows on later pages behave the same; deleting one does not re-fetch the page.
- A designed empty state for no reviews at all and for a filter that matches nothing.

**Seed.** The seed command creates reviews for roughly half of the eligible customer–product pairs among the demo world's non-cancelled orders, using its existing seeded random generator, with ratings that skew toward 4 and 5 and a few hand-written comments for the named demo customers. It decides eligibility with the same model-layer rule the views use, never reviews as staff, and never creates two reviews of one product by the same customer. At least one named demo customer is left with an eligible purchase they have not reviewed. Reviews are backdated after their orders. Reset is handled by the existing cascades.

**Testing.** pytest with plain shared fixtures, per the project convention. Tests cover at least:
- eligibility for each status (placed, shipped, and delivered allow; cancelled alone does not), for staff, for anonymous users, and after a review already exists;
- the unique constraint;
- rating range and comment validation, including whitespace-only;
- create, edit, and delete requiring sign-in and POST;
- a customer unable to edit or delete another customer's review (404);
- an owner whose only order was cancelled: can delete, cannot edit;
- the staff form ignoring a submitted rating;
- staff unable to create;
- the "Your review" slot's state for each kind of viewer;
- the summary, including the out-of-band refresh and the empty case;
- the "(edited)" property;
- the public-name property and its fallback;
- the catalog annotation;
- the back-office list's staff gate, ordering, pagination, and rating filter;
- the cascades on product and user deletion.

**Documentation.** The project layout section of CLAUDE.md gains the reviews app and its one-way import rule.

## Out of Scope

- **Review analytics on the staff dashboard** (top- and lowest-rated products, rating distribution, reviews over time). Deferred; it would read only data this feature already stores.
- Paginating, sorting, or filtering reviews on the product page.
- Filtering the back-office Reviews tab by product, or searching comment text.
- Reviews written by staff, and any "staff" badge on reviews.
- Staff changing a review's rating.
- An "edited by staff" label separate from "(edited)".
- Hiding or deleting reviews automatically when the order behind them is cancelled.
- Requiring delivery before a customer can review.
- Half-star ratings, review titles, photos, or pros/cons lists.
- Customers replying to reviews, the store responding publicly, and "Was this helpful?" votes.
- Reporting or flagging reviews for staff attention, and any approval queue before a review is published.
- A customer's own "My reviews" page.
- Emails or notifications about new reviews.
- Sorting the catalog by rating.

## Further Notes

- Reviews deliberately differ from order lines on deletion: an order is a financial record that must outlive the catalog, so its lines snapshot the product; a review only matters on its product's page, so it goes when the product goes. "Mark unavailable" remains the way to retire a product and keep its reviews.
- The page only decides what to *show*; the server enforces every rule on every request. A customer whose eligibility changed in another tab gets a refusal, not a review.
- A user who reviewed products as a customer and is later made staff becomes a moderator for those reviews too: they get the comment-only form, consistent with "staff are always moderators, never owners."
- The username fallback for the public name exposes the username of any customer with no name on file. The demo customers all have names; a gentler fallback (such as "Verified buyer") is a one-line change if this becomes a concern.
- Every review is from a verified buyer by construction, so no "verified purchase" badge is needed.
