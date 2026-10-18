# Plan: The ThoughtTronix Store — Customer Product Reviews

> Source PRD: `prd/product-reviews.md`. The PRD owns the requirements; this plan owns the sequence. Where a phase says "per the PRD," the PRD's wording is authoritative.

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: a new `reviews` app, following the `coupons` precedent: model, forms, customer views, back-office views, templates, and tests together. Storefront touch points live in `products` (catalog cards, product page, delete confirmation), `orders` (order detail links), and `dashboard` (tiles). `CLAUDE.md`'s project layout gains a `reviews/` entry in Phase 1.
- **URLs**: every URL is named under the `reviews` namespace, included at the root like the other apps.
  - Write / edit review: one login-required URL per product, keyed by product slug (e.g. `/products/<slug>/review/`).
  - Delete review: login-required, with a confirmation page.
  - Back office: `/backoffice/reviews/` (list, with a hidden-only filter) and a pk-keyed POST endpoint to toggle hide / unhide.
- **Models**: `Review` has the following:
  - `user` FK to `accounts.User` and `product` FK to `products.Product`, both `CASCADE`.
  - `rating`, a small positive integer from 1 to 5, enforced by validators.
  - `comment`, required.
  - `is_hidden`, defaulting to false.
  - `created_at`, defaulting to now (not `auto_now_add`, so the seed can backdate), and `updated_at` with `auto_now`.
  - A `UniqueConstraint` on (user, product) and newest-first default ordering.
  - An "edited" property, computed rather than stored.
  - One migration in Phase 1 creates the model.
- **Eligibility**: one manager method decides whether a user may **create** a review for a product. The user must be signed in, not `is_staff`, have a `DELIVERED` order line for the product, and have no existing review of it. It is checked only at creation. Editing requires ownership. Deleting requires ownership and a review that isn't hidden. Every entry point (product page, order page, the form URL, the seed) uses this method.
- **Querysets**: `Review` querysets gain `visible()`. `ProductQuerySet` gains `with_ratings()`, which annotates the average and count of visible reviews in one query. Every shopper-facing listing, average, and count is built on `visible()`.
- **Deep modules**: no new service module; the project keeps exactly three. The dashboard functions are added to `dashboard/queries.py` in its existing style: an optional `since`, docstrings, and type hints.
- **Auth / authorization**: customer views are login-required, and ineligible or non-owner access returns 403. Back-office views use the existing staff-required mixin. The new tab uses `section = "reviews"`. Staff never write reviews and never see review links.
- **Templates**: customer flows are ordinary multi-page forms extending `base.html`. The star rating uses DaisyUI rating radio inputs, with no JavaScript. Only the back-office toggle uses HTMX, and it returns a `_`-prefixed row partial. Every list gets a designed empty state.

---

## Phase 1: Tracer bullet — write a review and see it on the product page

**User stories**: 3, 4, 5, 7, 8, 9, 11, 12, 13, 15

### What to build

Create the `reviews` app with the `Review` model and its migration, the eligibility manager method, and `visible()`. A review form takes a 1–5 star rating and a comment. Comments shorter than 20 characters after trimming are rejected with a friendly error. The write URL checks eligibility and returns 403 to ineligible users. On success it redirects to the product page with a success message. The product page shows the following:

- a "Write a review" button for eligible customers only;
- the average rating and review count;
- every visible review, newest first, with its stars, comment, author, and date;
- a designed empty state explaining that reviews come from customers whose orders were delivered.

New conftest fixtures cover a customer with a delivered order and an existing review. Add the `reviews/` entry to `CLAUDE.md`'s project layout.

### Acceptance criteria

- [ ] Eligibility is allowed with a delivered order. It is refused for placed, shipped, and cancelled orders, for no order, for staff (even with a delivered order), for anonymous users, and when a review already exists.
- [ ] The database rejects a second review for the same (user, product), and the validators reject ratings outside 1–5.
- [ ] Deleting a product or a user cascades to their reviews, and `visible()` excludes hidden reviews.
- [ ] The form rejects comments under 20 characters, including whitespace-padded ones, and rejects out-of-range ratings.
- [ ] An eligible customer can post a review and lands on the product page with a success message. An ineligible user who reaches the URL directly gets 403.
- [ ] The product page shows the average, the count, and the reviews newest first, or the designed empty state.
- [ ] The "Write a review" button appears only for eligible customers.
- [ ] `CLAUDE.md` lists the `reviews` app, and the full suite is green.

---

## Phase 2: Edit your review

**User stories**: 6, 14, 16, 17, 18

### What to build

When the signed-in user already has a review for the product, the write URL shows the edit form, prefilled. Editing needs only ownership, not eligibility, so it still works after the order is cancelled. The product page button reads "Edit your review." Edited reviews show an "edited" marker. The viewer's own review is pinned at the top of the list.

### Acceptance criteria

- [ ] An existing review opens in the edit form, and saving updates it (no duplicate) and redirects with a success message.
- [ ] Editing still works after the customer's order is moved to cancelled.
- [ ] The product page says "Edit your review" for a customer who has reviewed the product.
- [ ] The "edited" property is true only when `updated_at` is meaningfully later than `created_at`, and the marker renders accordingly.
- [ ] The viewer's own review appears first, ahead of newer reviews by others.

---

## Phase 3: Delete your review

**User stories**: 19, 20

### What to build

A delete URL with a confirmation page. Confirming deletes the review and redirects to the product page with a success message. Someone else's review returns 403. The author's own review shows a Delete action on the product page. After deleting, the customer is eligible again and sees "Write a review."

### Acceptance criteria

- [ ] The owner sees a confirmation page, and confirming deletes the review and redirects with a success message.
- [ ] Attempting to delete someone else's review returns 403.
- [ ] After deleting a visible review, the customer can write a new one for the same product.

---

## Phase 4: Ratings on catalog and category cards

**User stories**: 1, 2

### What to build

Add `ProductQuerySet.with_ratings()`, which annotates the average rating and count of visible reviews in a single query. The catalog view applies it, and the category view inherits it. Each card shows "★ average (count)" or "No reviews yet."

### Acceptance criteria

- [ ] Cards show the rounded average and count for reviewed products and "No reviews yet" otherwise.
- [ ] Hidden reviews are excluded from the annotation.
- [ ] Category pages show the same ratings.
- [ ] A query-count test shows the catalog's query count does not grow with the number of products.

---

## Phase 5: Review links on the order detail page

**User stories**: 10, 16 (order page)

### What to build

On the customer's order detail page, each line of a `DELIVERED` order whose product still exists shows a link. It reads "Review this product" or "Edit your review," depending on whether the customer has reviewed it, and points to the write / edit URL. Lines in other statuses and lines whose product was deleted show nothing. Staff never see these links.

### Acceptance criteria

- [ ] Delivered lines show "Review this product" or "Edit your review" correctly.
- [ ] Placed, shipped, and cancelled orders' lines show no link.
- [ ] A line whose product was deleted shows no link.
- [ ] The page does not issue a query per line to decide the link.

---

## Phase 6: Back-office Reviews tab — list, filter, and product-delete warning

**User stories**: 22, 23, 24, 29

### What to build

A new **Reviews** tab in the staff tab rail (`section = "reviews"`) leading to `/backoffice/reviews/`. It lists every review newest first, with product, author, rating, comment, date, and hidden status. A filter restricts it to hidden reviews, and a designed empty state covers both the unfiltered and filtered views. The back-office product delete confirmation states how many reviews will be deleted with the product.

### Acceptance criteria

- [ ] Only staff can reach the list. Customers get the existing staff-required behavior, and anonymous users are redirected to sign in.
- [ ] The list shows all reviews (hidden included) newest first, and the hidden filter shows only hidden ones.
- [ ] The empty state renders when there are no matching reviews.
- [ ] The Reviews tab is highlighted on this page.
- [ ] The product delete confirmation shows the correct review count.

---

## Phase 7: Hide / unhide moderation

**User stories**: 21, 25, 26, 27, 28

### What to build

Each back-office row gets a Hide / Unhide button submitted with HTMX as a POST. The endpoint flips `is_hidden` and returns the re-rendered row partial. Staff cannot change a review's text or rating. Once hidden, a review disappears from the storefront list, the averages, and the counts. Its author still sees it pinned on the product page, labeled "Hidden by staff," with Edit but no Delete. Attempting to delete a hidden review returns 403, so hiding can't be sidestepped by deleting and re-posting.

### Acceptance criteria

- [ ] The toggle is staff-only and POST-only, and returns the row partial with the flipped state.
- [ ] A hidden review is absent from the product page for other viewers and is excluded from the product-page and card averages and counts.
- [ ] The author sees their hidden review pinned and labeled "Hidden by staff," with an Edit button and no Delete button.
- [ ] The author can still edit a hidden review.
- [ ] Deleting a hidden review returns 403, and the author remains ineligible to write a new one.
- [ ] Unhiding restores the review everywhere.

---

## Phase 8: Dashboard tiles

**User stories**: 30, 31

### What to build

Add two public functions to the dashboard queries module, each with an optional `since`, a docstring, and type hints: the average rating of visible reviews, and the count of visible reviews created since the given time. The average returns `None` when there are no reviews. The dashboard renders them as two new stat tiles that follow the existing period selection, with a placeholder when there is no average.

### Acceptance criteria

- [ ] Both functions respect `since` and exclude hidden reviews.
- [ ] The average returns `None` with no reviews, and the tile shows a placeholder.
- [ ] The tiles change with the dashboard's period selection.

---

## Phase 9: Seed the demo world

**User stories**: 32, 33

### What to build

The seed creates reviews with its existing seeded random generator, so every run produces the same world. Background customers review a portion of their delivered order lines with a realistic spread of ratings. Comments are drawn from a pool of hand-written, in-universe comments, and backdated `created_at` values fall after the order date. One or two reviews are hidden. The demo `customer` has an existing review of MindSync and leaves SyncRest and DreamWeaver unreviewed. Every seeded review is created only for a (user, product) pair the eligibility method approves. The existing wipe already covers reviews through cascades.

### Acceptance criteria

- [ ] Running `seed` twice produces the same reviews, and the seed stays idempotent.
- [ ] Several products have reviews, and at least one review is hidden.
- [ ] `customer` sees "Edit your review" for MindSync, and "Review this product" for SyncRest and DreamWeaver, on both the product pages and the delivered orders.
- [ ] Every seeded review satisfies the eligibility rule at creation and is dated after its order.
- [ ] The PRD's "How to demo" walkthrough works end to end after a fresh seed, and the full suite is green (tests still never invoke `seed`).
