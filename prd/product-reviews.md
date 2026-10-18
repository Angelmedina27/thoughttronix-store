# PRD: The ThoughtTronix Store — Customer Product Reviews

*Commissioned by ThoughtTronix Product Management. "Your Thoughts, Our Business."*

---

## Problem Statement

A shopper deciding whether to buy a neural implant, a home hub, or a wearable has only ThoughtTronix's own word to go on: the tagline, the description, and the price. There is no way to hear from the people who already bought it. Nothing on a product page or a catalog card says whether customers were happy, disappointed, or somewhere in between, so every purchase is a leap of faith — and for products this personal, that is a real barrier.

Customers who *have* bought something have nowhere to say how it went. A delighted customer can't vouch for a product; an unhappy one can't warn the next buyer. Their experience disappears after delivery.

Staff are just as blind. The dashboard reports revenue and order counts, but nothing about how customers feel about what they received. There is no signal for which products are pleasing people and which are not.

## Solution

**Customer product reviews**: a star rating and a written comment, left by people who actually received the product.

- **Verified buyers only.** A customer can review a product once an order containing it has been **delivered**. Staff accounts never write reviews — they moderate them.
- **One review per customer per product.** A returning customer edits their existing review rather than writing a second one. Edited reviews are marked "edited."
- **Easy to find.** A "Write a review" (or "Edit your review") button appears on the product page for eligible customers, and a "Review this product" link appears beside each line of a delivered order in the customer's order history.
- **Ratings everywhere shoppers browse.** Every catalog and category card shows the product's average rating and review count, or "No reviews yet." The product page shows the average, the count, and every visible review, newest first.
- **Customers stay in control.** A customer can edit their review at any time, and delete it unless staff have hidden it.
- **Staff moderation.** Reviews go live immediately. A new **Reviews** tab in the back office lets staff hide an inappropriate review — and unhide it — without destroying it.
- **Dashboard signal.** Two new stat tiles show the average rating and the number of reviews posted in the selected period.

## User Stories

**Shopper (browsing)**

1. As a shopper, I want to see each product's average star rating and review count on catalog and category cards, so that I can compare products while browsing.
2. As a shopper, I want products without reviews to say "No reviews yet" rather than show zero stars, so that a new product isn't mistaken for a badly rated one.
3. As a shopper, I want the product page to show the average rating and how many reviews it is based on, so that I can judge how much to trust the average.
4. As a shopper, I want to read every visible review on the product page, newest first, so that I see the most current opinions first.
5. As a shopper, I want each review to show its star rating, comment, author, and date, so that I can weigh individual opinions.
6. As a shopper, I want to see when a review has been edited, so that I know the opinion may have changed since it was first posted.
7. As a shopper, I want to know that every review comes from a customer who received the product, so that I can trust the reviews aren't fake.
8. As a shopper, I want a product with no reviews to show a clear, friendly message explaining that reviews come from customers whose orders were delivered, so that the empty section doesn't look broken.

**Customer (writing a review)**

9. As a customer whose order was delivered, I want a "Write a review" button on the product page, so that I can share my experience.
10. As a customer, I want a "Review this product" link next to each item in my delivered orders, so that I can review purchases right where I check on them.
11. As a customer, I want to give a rating from 1 to 5 stars and write a comment, so that my review captures both a score and the reason for it.
12. As a customer, I want to be told if my comment is too short, so that I know what the form needs before it accepts my review.
13. As a customer, I want to return to the product page with a success message after posting, so that I can see my review is live.
14. As a customer, I want my own review pinned at the top of the product's review list, so that I can find it without scrolling.
15. As a customer whose order hasn't been delivered yet, I want no review button to appear, so that I'm not offered something I can't do yet.

**Customer (managing a review)**

16. As a customer who already reviewed a product, I want the product page and my order page to say "Edit your review" instead of "Write a review," so that I update my opinion rather than duplicate it.
17. As a customer, I want to edit my rating and comment at any time, so that my review reflects my experience after months of use.
18. As a customer, I want to keep the ability to edit my review even if my order is later cancelled or refunded, so that I can still correct my own words.
19. As a customer, I want to delete my review after confirming, so that I can withdraw an opinion I no longer stand behind.
20. As a customer who deleted a review, I want to be able to write a new one for the same product, so that deleting isn't a permanent loss of my voice.
21. As a customer whose review was hidden by staff, I want to still see it on the product page marked "Hidden by staff," so that I understand why other shoppers can't see it.

**Staff (moderation)**

22. As a staff member, I want a Reviews tab in the back office, so that I can see every review in one place.
23. As a staff member, I want reviews listed newest first, with the product, author, rating, comment, and date, so that I can spot new problems quickly.
24. As a staff member, I want to filter the list to show only hidden reviews, so that I can revisit past moderation decisions.
25. As a staff member, I want to hide a review with one click, without leaving the page, so that inappropriate content disappears from the storefront immediately.
26. As a staff member, I want to unhide a review, so that a mistaken or reconsidered moderation decision can be reversed.
27. As a staff member, I want hidden reviews excluded from averages, counts, and the dashboard, so that spam can't skew the numbers.
28. As a staff member, I want a customer to be unable to delete a hidden review and post a fresh one, so that hiding can't be sidestepped.
29. As a staff member, I want the product delete confirmation to tell me how many reviews will be deleted along with the product, so that I understand what I'm about to lose and can choose to mark it unavailable instead.

**Staff (analytics)**

30. As a staff member, I want the dashboard to show the average rating across all visible reviews, so that I can see overall customer satisfaction at a glance.
31. As a staff member, I want the dashboard to show how many reviews were posted in the selected period, so that I can see how engaged customers are.

**Demo**

32. As someone demoing the store, I want the seeded store to already have reviews on several products, including a hidden one, so that every part of the feature is visible right after seeding.
33. As someone demoing the store, I want the demo customer to have one existing review and other delivered products still waiting for a review, so that I can show both writing and editing a review live.

## Implementation Decisions

**New `reviews` app**

- Reviews live in a new app with its own `reviews` URL namespace, following the precedent of the `coupons` app: model, forms, customer views, back-office views, templates, and tests together.
- The project CLAUDE.md's project layout gains an entry for the new app in the same change.

**Review model**

- Fields: the author (FK to the user model), the product (FK to `Product`), a rating (small positive integer, 1–5, enforced by validators), a required comment, an `is_hidden` flag defaulting to false, and `created_at` / `updated_at` timestamps.
- `created_at` uses a default of "now" rather than auto-assignment, matching `Order`, so the seed can backdate reviews. `updated_at` updates on every save.
- A database `UniqueConstraint` on (user, product) enforces one review per customer per product.
- Both foreign keys use `CASCADE`: deleting a product deletes its reviews; deleting a user deletes theirs. This matches how carts and orders already treat deleted users. Retiring a product with `is_available = False` keeps it and its reviews.
- Default ordering is newest first.
- A review is "edited" when `updated_at` is meaningfully later than `created_at`; this is a model property, not a stored field.

**Eligibility rule — one place**

- A manager method decides whether a given user may **create** a review for a given product: the user is signed in, is **not** `is_staff`, has an order line for the product in an order whose status is `DELIVERED`, and has no existing review for it.
- Eligibility is checked **only when creating**. Reviews are not re-checked later; a review stays if its order is later cancelled or moved to another status.
- Editing requires only that the review belongs to the signed-in user. Deleting requires ownership **and** that the review is not hidden.
- Every entry point — product page button, order page links, the form URL itself, and the seed — goes through this one method. No new service module is created; the project keeps exactly three deliberate deep modules.

**Querysets**

- The review queryset gains `visible()`, excluding hidden reviews. Every shopper-facing listing, average, and count uses it.
- `ProductQuerySet` gains `with_ratings()`, annotating each product with its average rating and count of **visible** reviews in a single query. The catalog view applies it, so the category view inherits it.

**Form**

- A review form with the rating and comment. The comment must be at least 20 characters after trimming; the form owns this validation and shows a friendly error.
- The rating renders as DaisyUI rating inputs (radio buttons styled as stars) — no JavaScript.

**Customer views and URLs (`reviews` namespace)**

- **Write / edit review** — one login-required URL per product (keyed by product slug, like the public catalog). If the user already has a review for the product, it shows the edit form; otherwise it checks eligibility and shows the create form. Ineligible users who reach the URL directly receive 403. On success, redirect to the product page with a success message.
- **Delete review** — login required; a confirmation page, then deletion and a redirect to the product page with a success message. A hidden review, or someone else's review, returns 403.
- These are ordinary multi-page form flows, not HTMX.

**Storefront changes (`products` and `orders`)**

- **Catalog and category cards** show "★ average (count)" or "No reviews yet," from the `with_ratings()` annotation.
- **Product detail page** shows the average and count, a "Write a review" / "Edit your review" button when appropriate, and the list of visible reviews, newest first, with no pagination. The viewer's own review is pinned at the top — including a hidden one, marked "Hidden by staff," with its Edit button (and no Delete button). The empty state is designed, per the project's template conventions.
- **Order detail page** shows, beside each line of a `DELIVERED` order whose product still exists, either "Review this product" or "Edit your review," linking to the write / edit URL. Lines of other statuses, and lines whose product was deleted, show no link. Staff never see these links.
- **Product delete confirmation** (back office) states how many reviews will be deleted with the product.

**Back office**

- A new **Reviews** tab in the staff tab rail, using the existing `section` context convention (`reviews`).
- The list view is staff-only, shows all reviews newest first, and has a filter for hidden reviews only. It has a designed empty state.
- Each row has a Hide / Unhide toggle submitted with HTMX; the endpoint flips `is_hidden` and returns the re-rendered row partial. The toggle is a POST.
- Staff cannot edit a review's text or rating, only hide or unhide it.

**Dashboard (`dashboard` queries module)**

- Two new public functions following the module's existing pattern (an optional `since` datetime, docstrings, type hints): the average rating of visible reviews, and the count of visible reviews, each limited to reviews created since the given time.
- The average returns nothing (rather than zero) when there are no reviews, and the tile shows a placeholder.
- The dashboard shows them as two additional stat tiles, respecting the dashboard's existing period selection.

**Seed data**

- The seed wipes and recreates reviews along with everything else; because reviews cascade from users and products, the existing wipe covers them.
- Reviews are generated with the seed's existing seeded random generator, so every run produces the same world.
- Background customers review a portion of their delivered order lines, with a realistic spread of ratings and comments drawn from a pool of hand-written, in-universe comments. Backdated `created_at` values fall after the order's date.
- One or two seeded reviews are hidden, so the staff tab's hidden filter has content.
- The demo `customer` has an existing review of MindSync. Their other delivered products (SyncRest, DreamWeaver) remain unreviewed.
- Every seeded review is created only for a (user, product) pair the eligibility method approves.

## Out of Scope

- **Sorting or filtering the catalog by rating** ("Top rated," "4★ & up").
- **A rating breakdown** (count of reviews per star level) on the product page.
- **Pagination or "show more"** for reviews.
- **Review titles, photos, pros/cons, or "would recommend"** fields.
- **Pre-moderation.** Reviews are never held for approval.
- **Customer flagging / "Report this review."**
- **Helpfulness voting** ("Was this review helpful?").
- **Staff replies** to reviews.
- **Staff editing** a review's content.
- **A "lowest-rated" or "top-rated" products table** on the dashboard, or any review analytics beyond the two tiles.
- **A cached average** stored on `Product`; averages are always computed from reviews.
- **Re-checking eligibility after an order changes status**, or removing reviews when an order is cancelled.
- **Guarding order status transitions** in the back-office order status form (still any status, any time).
- **Notifications** (emailing customers to request a review, or staff when a review is posted).
- **Reviews by staff**, with or without an employee badge.

## Testing Decisions

- Tests use pytest + pytest-django with plain fixtures in the project-level conftest, as for the rest of the suite. Tests never invoke the seed command. New fixtures cover a delivered order for a customer and an existing review.
- **Eligibility** is tested directly on the manager method: allowed with a delivered order; refused for placed, shipped, and cancelled orders, for no order at all, for staff (even with a delivered order), for anonymous users, and when a review already exists.
- **Model tests** cover the unique constraint, rating bounds, the "edited" property, cascade on product and user deletion, and `visible()`.
- **Form tests** cover the 20-character minimum (including whitespace-only padding) and rating bounds.
- **Customer view tests** cover create, edit, and delete; 403 for ineligible creation, someone else's review, and deleting a hidden review; editing still allowed after the order is cancelled; editing a hidden review; and that deleting a visible review allows writing a new one.
- **Display tests** cover hidden reviews excluded from the product page, averages, and counts; the author's own hidden review pinned and labeled; the empty state; and the order page showing the right link per line status.
- **Query-count test**: the catalog page's number of queries does not grow with the number of products.
- **Back-office tests** cover staff-only access, the hidden filter, and the HTMX toggle returning the row partial.
- **Dashboard tests** cover the two new functions, including the `since` filter, exclusion of hidden reviews, and the no-reviews case.
- The suite stays green at the end of every phase.

## Further Notes

**How to demo.** Run `seed`, browse the catalog to see star averages on cards, and open a reviewed product to see its reviews. Sign in as `customer`: the MindSync page and its delivered order show "Edit your review," while SyncRest and DreamWeaver offer "Review this product." Write one, then sign in as a staff member to hide it from the Reviews tab and watch it leave the storefront and the dashboard tiles.

**Why check eligibility only at creation.** A review is an opinion about an experience the customer really had; a later refund doesn't erase that experience, and is often the most useful thing a shopper can read about. Checking once keeps the rule in one place instead of a condition repeated in every listing and average. Removing a review is a deliberate staff action (hiding), not a side effect of the order status dropdown — which, today, staff can set to any value at any time.

**Why hiding instead of deleting.** Hiding is reversible, so a moderation mistake costs nothing. Customers can still delete their own visible reviews; blocking deletion of hidden ones prevents a "delete and re-post" end-run around moderation.

**Why `CASCADE` on product.** The store already has a soft retirement path (`is_available = False`). Hard deletion is the deliberate "this should not exist" action, so its reviews go with it — and the confirmation page says so.
