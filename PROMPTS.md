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

## 2026-10-18 — Product Reviews Phase 9: seed the demo world with reviews

### Prompts
1. `/implement @prd/product-reviews.md @plans/product-reviews.md implement phase 9`
2. YEs, go ahead without TDD
3. How can I manually verify this phase in the browser?
4. Update PROMPTS.md with the standard prompt for completing Phase 9

### Summary
- **Outcome:** Implemented Phase 9 of `plans/product-reviews.md` (user stories 32 and 33) in `products/management/commands/seed.py`. A fresh seed now reports 44 reviews across 22 products, 2 of them hidden.
  - **One RNG:** `handle()` creates the existing `random.Random(2026)` and passes it to `_create_orders(rng)` and then the new `_create_reviews(rng)`. Orders consume it in the same order as before, so the order history is unchanged.
  - **Demo customer:** `CUSTOMER_REVIEW` gives `customer` a 4★ MindSync review, dated 10 days after the delivered order and edited 40 days after that, so the "edited" marker has a demo. SyncRest and DreamWeaver stay unreviewed.
  - **Background reviews:** About 60% (`REVIEW_RATE`) of background customers' delivered order lines are reviewed. They are walked in a fixed order (`order__created_at`, `pk`), and every review is gated on `Review.objects.can_create`, which also skips repeat purchases of a product. Ratings come from `RATING_WEIGHTS` (40/30/15/10/5 for 5★ down to 1★). Comments come from `REVIEW_COMMENTS`, hand-written in-universe lines in "glowing," "mixed," and "unhappy" pools chosen by rating. `created_at` falls 3–30 days after the order, capped at an hour before now.
  - **Hidden reviews:** Two background reviews, picked with the RNG, are rewritten with the `HIDDEN_COMMENTS` spam text, set to 1★, and hidden.
  - **Backdating:** A `_build_review` helper writes `updated_at` back to `created_at` with a queryset `.update()` (or to an explicit later time for the MindSync review). Without it, `auto_now` would stamp "now" and every backdated review would read as edited.
  - **Docs and output:** The module and `_wipe` docstrings note the customer's review and the cascade wipe, and the success message prints the review count.
  - **Checks:** A shell script run after two consecutive seeds found the following:
    - identical review digests across the two runs;
    - 0 reviews dated before their delivered order;
    - only `customer`/MindSync marked edited;
    - 18 visible reviews in the last 30 days.
  - **Walkthrough:** A test-client walkthrough confirmed "Edit your review" on MindSync, "Write a review" on SyncRest and DreamWeaver, the right link on each delivered order line, and no hidden comment on the public page.
  - **Suite and lint:** The full suite passed (377 in 4.5 minutes; no new tests, since tests never invoke `seed`), and `ruff check` and `ruff format` were clean. Nothing was committed.
- **Deviations:** The `tdd` skill found no candidates, because the phase is seed data and tests never invoke `seed`. The user approved skipping TDD along with the proposed plan, including the assistant's added decision to show the customer's review as edited. The user asked for the browser verification steps again (prompt 3), and the assistant gave a fuller walkthrough with URLs. The user asked for this entry without explicitly confirming the browser check passed.
- **Sideways:**
  - **Quoting:** A heredoc-driven Python script for the edits failed on shell quoting, so the edits were made with the Edit tool instead.
  - **Checks:** The first idempotence check compared Python `hash()` values, which are randomized per process, so the two runs looked different. It was switched to a SHA-256 digest of the rows. The first date check filtered on a literal `"delivered"` status and reported all 44 reviews as bad, until it was switched to `Order.Status.DELIVERED`. The check script also crashed printing `★` to the cp1252 console.
  - **Lint:** `ruff check` flagged two `zip()` calls missing `strict=` (B905); both now pass `strict=True`.
  - **Hung test run:** The first full test run sat nearly idle for about 18 minutes behind a `| tail -3` that hid its progress. It was killed and rerun with verbose output to a log, and that run finished normally in 4.5 minutes. The cause wasn't found.
  - **Catalog page 1:** The test-client walkthrough found no "No reviews yet" cards there, because the first 12 products all have reviews; the unreviewed ones are on later pages.

## 2026-10-17 — Product Reviews Phase 8: dashboard review tiles (TDD)

### Prompts
1. `/implement @prd/product-reviews.md @plans/product-reviews.md implement phase 8`
2. Yes I approve those three
3. Yes keep it as a float, I approve
4. move onto cycle 2
5. Yes write the code to make it pass
6. Move onto cycle 3
7. Write the code to make it pass
8. How can I manually verify this phase in the browser?
9. Update PROMPTS.md with the standard prompt for completing Phase 8

### Summary
- **Outcome:** Implemented Phase 8 of `plans/product-reviews.md` (user stories 30 and 31) through the `implement` skill, which handed three behaviors to `tdd`.
  - **Queries:** `dashboard/queries.py` gains a private `_visible_reviews(since)`, built on `Review.objects.visible()` with the `since` cutoff and mirroring `_sold(since)`. Two public functions sit on top of it, each with a docstring and type hints: `average_rating(since) -> float | None` (Django's `Avg`, which is `None` with no reviews) and `review_count(since) -> int`. The module docstring now says seven functions and one of three deep modules, and that review functions exclude hidden reviews while sales functions exclude cancelled orders.
  - **Tiles:** `DashboardView` passes both values for the selected period. `dashboard.html` adds a second stats row: **Average rating** ("4.5 / 5", "from N visible review(s)", or "—" with "No reviews in this period") and **Reviews posted** (the count, with "<period>, excluding hidden reviews"). The row sits inside the existing `store_has_sales` branch; reviews require a delivered order, so a store with reviews always has sales.
  - **TDD behaviors:** (1) `average_rating` is `None` when empty, excludes hidden reviews, and respects `since` (4.5 over 30 days, 10/3 over all time); (2) `review_count` is 0 when empty, excludes hidden reviews, and respects `since` (2 vs 3); (3) the tiles follow the period, so 60-day-old reviews show the placeholder under the default 30 days and "4.5 / 5 … from 2 visible reviews" under All time. A `make_review` helper in `dashboard/tests.py` creates each review with a fresh customer and backdates it like `make_order`. Each test failed on an assertion before its code was written. Cycles 1 and 2 needed a stub function first, because the first run of cycle 1 failed with `AttributeError`.
  - **Checks:** the full suite passed (377), and `ruff check` and `ruff format` were clean. Nothing was committed.
- **Deviations:** No recommendation was overridden. The user accepted the three behaviors and each RED test as proposed. In cycle 1 the assistant asked whether the average should be a raw `float` or a rounded `Decimal` like `average_order_value`, and the user chose the `float`. The user asked for the browser verification steps again (prompt 8). The assistant gave a fuller walkthrough with the seeded logins, the customer's delivered MindSync/SyncRest order, expected numbers (3.5 / 5, then 5.0 / 5 after hiding), and a `manage.py shell` one-liner to backdate a review for the period check. The user asked for this entry before confirming the browser check, so this log records no manual verification of the phase.
- **Sideways:** The assistant's first edit to `dashboard/tests.py` inserted a stray `PLACEHOLDER_MARK` line in the wrong spot. It was reverted in the next edit, before any test ran. The first run of cycle 1 failed with `AttributeError` instead of an assertion; the assistant called it scaffolding, not RED, added a `None`-returning stub, and folded the empty-store `None` check into the test before showing it for approval. The full suite took about 4.5 minutes.

## 2026-10-17 — Product Reviews Phase 7: hide / unhide moderation (TDD)

### Prompts
1. `/implement @prd/product-reviews.md @plans/product-reviews.md implement phase 7`
2. I approve the three. go ahead
3. I approve go ahead
4. Yes Im ready for cycle 2
5. I approve the test go ahead
6. Go ahead with cycle 3
7. I approve go ahead
8. Go ahead with the rest of phase 7
9. Did the test pass then?
10. How can I manually verify this phase in the browser?
11. Update PROMPTS.md with the standard prompt for completing Phase 7

### Summary
- **Outcome:** Implemented Phase 7 of `plans/product-reviews.md` (user stories 21, 25, 26, 27, and 28) through the `implement` skill, which handed three behaviors to `tdd`.
  - **Toggle:** `Review.toggle_hidden()` flips `is_hidden` and saves only that field. `ToggleReviewHiddenView` (`StaffRequiredMixin` with a `post`-only `View`) serves `reviews:toggle_hidden` at `/backoffice/reviews/<pk>/toggle-hidden/` and returns `_review_row.html`. Each row gains a Hide / Unhide button (`hx-post`, `hx-target="closest tr"`, `hx-swap="outerHTML"`), and the CSRF token comes from the `hx-headers` already on `<body>`. Staff can change only the hidden flag, never a review's text or rating.
  - **Author's view:** `ProductDetailView` now takes the viewer's own review from all of the product's reviews, not just `visible()`. A hidden review still appears pinned for its author and never counts toward the list, the average, or the count. `_review_card.html` shows a "Hidden by staff" badge and hides the Delete link on hidden reviews; "Edit your review" stays.
  - **Delete rule:** a new `Review.can_be_deleted_by(user)` (author and not hidden) drives `ReviewDeleteView.test_func`, so GET and POST on a hidden review return 403. The review stays, and `can_create` keeps the author from posting a new one.
  - **TDD behaviors:** (1) the toggle hides a review and returns only its row partial with an Unhide button; (2) the author sees their hidden review pinned above a newer one, labeled "Hidden by staff", with Edit and no Delete link; (3) deleting a hidden review is 403 on GET and POST, the review remains, and the author is still ineligible. Each failed on an assertion before its code was written. Cycle 1 needed a stub URL and view first, so the failure came from the missing flip rather than a missing route.
  - **Other tests:** unhide, the toggle leaving text and rating untouched, POST-only (405 on GET), customers get 403, anonymous users are sent to sign in, 404 for an unknown review, each row offering its toggle, editing a hidden review (it stays hidden), hidden reviews left out of the product-page average and count (including the author's own), hidden reviews left out of card averages alongside a visible one, and unhiding restoring the review, average, count, and card rating.
  - **Checks:** the full suite passed (374), and `ruff check` and `ruff format` were clean. Nothing was committed.
- **Deviations:** No recommendation was overridden, and the user accepted the three behaviors and each RED test as proposed. The user asked whether the tests had passed (prompt 9) while the full suite was still running in the background. The assistant said it couldn't tell yet and reported the result, 374 passed, once the run finished. The user asked for the browser verification steps again (prompt 10), and the assistant restated them. The user asked for this entry before confirming the browser check that the `implement` skill asks for, so this log does not record a manual verification of the phase.
- **Sideways:** The assistant's first edit script wrote with Python's default Windows codepage, so two new em dashes were saved as a cp1252 `0x97` byte. The test run that followed failed with `SyntaxError: Non-UTF-8 code`. The assistant re-encoded only those stray bytes to UTF-8, checked `git diff --stat` to confirm no other content had changed, and wrote every later edit with `encoding="utf-8"`. A first draft of the unhide test's "Hide button" assertion was clumsy; it was replaced with a `re.search` before the test ever ran. The full suite outlasted the two-minute foreground timeout and finished in the background (about 4.5 minutes).

## 2026-10-17 — Product Reviews Phase 6: back-office Reviews tab and product-delete warning (TDD)

### Prompts
1. `/implement @prd/product-reviews.md @plans/product-reviews.md implement phase 6`
2. I approve go ahead
3. I approve go ahead
4. Go ahead I approve
5. I approve
6. Go ahead
7. How can I manually verify this phase in the browser?
8. Update PROMPTS.md with the standard prompt.

### Summary
- **Outcome:** Implemented Phase 6 of `plans/product-reviews.md` (user stories 22, 23, 24, and 29) through the `implement` skill, which handed three behaviors to `tdd`. The staff tab rail in `templates/backoffice/base.html` gains a **Reviews** tab between Orders and Dashboard.
  - **Staff list:** `ManageReviewListView` in `reviews/views.py`, behind `StaffRequiredMixin`, serves `reviews:manage_reviews` at `/backoffice/reviews/` with `section = "reviews"`. It lists every review, hidden ones included, newest first, with `select_related("user", "product")`. `?hidden=1` narrows the list through a new `ReviewQuerySet.hidden()`, the counterpart of `visible()`.
  - **Templates:** each row (product link, author, stars, comment, date with an "edited" note, Hidden/Visible badge) is its own partial, `templates/reviews/partials/_review_row.html`, ready for Phase 7's HTMX toggle. `templates/reviews/manage_reviews.html` has "all / hidden only" filter badges like the Orders status filter, plus two designed empty states: "No reviews yet" and "No hidden reviews".
  - **Delete warning:** the product delete confirmation reads `product.reviews.count`, which includes hidden reviews because the cascade deletes them too. It warns "Its N reviews will be deleted too" and suggests marking the product unavailable instead.
  - **TDD behaviors:** (1) the list shows every review, hidden included, newest first; (2) the hidden filter shows only hidden reviews; (3) the delete confirmation counts hidden reviews ("2 reviews" for one visible plus one hidden). Each behavior had a RED step that failed on an assertion before its code was written.
  - **Other tests:** anonymous users are sent to sign in, customers get 403, the Reviews tab is highlighted, and both empty states render. That makes seven tests in the new `reviews/test_backoffice.py` and one in `products/test_backoffice.py`.
  - **Checks:** the full suite passed (358), and `ruff check` and `ruff format` were clean. Nothing was committed.
- **Deviations:** No recommendation was overridden, and the user accepted the three behaviors and each RED test as proposed. The assistant gave the browser verification steps once the feedback loops passed. The user then asked for them again (prompt 7), and the assistant restated them in more detail. Because the seed has no reviews until Phase 9, those steps have the tester write reviews as `customer` and hide one through `/admin/`. The user asked for this entry before confirming the browser check that the `implement` skill asks for, so this log does not record a manual verification of the phase.
- **Sideways:** The first version of the tab-highlight test matched the tab's exact HTML whitespace. The assistant's script that wrote it turned the escaped `\n` into a real newline, which broke the f-string (`SyntaxError: unterminated f-string literal`). The assistant replaced it with a whitespace-tolerant `re.search`, which also removed the dependency on template indentation. The first `ruff check` flagged import order in `reviews/views.py` (an extra blank line between first-party imports), and `ruff check --fix` corrected it.

## 2026-10-17 — Product Reviews Phase 5: review links on the order detail page (TDD)

### Prompts
1. `/implement @prd/product-reviews.md @plans/product-reviews.md implement phase 5`
2. I approve go ahead
3. Go ahead i approve
4. Move on to behavior 2
5. Move on to behavior 3
6. How can I manually verify this phase in the browser?
7. Go ahead and update PROMPTS.md for this phase using the standard format

### Summary
- **Outcome:** Implemented Phase 5 of `plans/product-reviews.md` (user stories 10, and 16 on the order page) through the `implement` skill, which handed three behaviors to `tdd`. `OrderDetailView` now adds two entries to the page context. `show_review_links` is true only for a `DELIVERED` order viewed by someone who isn't staff. `reviewed_product_ids` is the set of products the customer has reviewed, loaded in one query and only when links will show. The queryset prefetches `items__product`, so each line's product and slug cost no extra queries. `templates/orders/order_detail.html` shows "Edit your review" or "Review this product" under each eligible line whose product still exists, linking to `reviews:write`. TDD behaviors: (1) delivered lines show the right label and link; (2) placed, shipped, and cancelled orders show no link (parametrized); (3) the page's query count stays the same when five more lines are added, two of them reviewed. Ordinary tests cover a line whose product was deleted and staff viewing their own delivered order. That makes six new tests (eight cases) in `reviews/tests.py`. The full suite passed (350), and `ruff check` and `ruff format` were clean. Nothing was committed.
- **Deviations:** No recommendation was overridden, and the user accepted the three behaviors as proposed. The "Review this product" link doesn't call `Review.objects.can_create` per line, because that would cost one query per line, which acceptance criterion 4 forbids. On a delivered order viewed by a non-staff customer with no review of the product, the outcome is identical, and the write URL still checks `can_create` when the link is followed. The assistant pointed this out after behavior 1, and the user did not object. Behaviors 2 and 3 passed on their first runs because behavior 1's code already covered them, so neither had a RED step. To show the tests could fail, the assistant temporarily removed the status check (all three status cases failed) and reverted the prefetch to `items` (the query test failed with `12 == 7`), restoring the code each time. The user asked for this entry before confirming the browser check that the `implement` skill asks for, so this log does not record a manual verification of the phase.
- **Sideways:** At the start of behavior 2, `git diff` showed an uncommitted edit to `PROMPTS.md` that the assistant had not made: the Phase 4 entry gained "How can I manually verify this phase in the browser?" as prompt 8, and the next prompt was renumbered to 9. The assistant left it untouched, told the user, and it remains in the working tree alongside this entry.

## 2026-10-17 — Product Reviews Phase 4: ratings on catalog and category cards (TDD)

### Prompts
1. `/implement @prd/product-reviews.md @plans/product-reviews.md implement phase 4`
2. Yes go ahead with those three
3. Go ahead and make it pass yes
4. Yes move on to behavior 2
5. Yes go ahead and make it pass
6. Yes move on to behavior 3
7. Yes keep it and move on with the phase
8. How can I manually verify this phase in the browser?
9. Go ahead and update PROMPTS.md for this phase using the standard format.

### Summary
- **Outcome:** Implemented Phase 4 of `plans/product-reviews.md` (user stories 1, 2) through the `implement` skill, which handed three behaviors to `tdd`. (1) `ProductQuerySet.with_ratings()` adds `average_rating` and `review_count` to each product from visible reviews only, using `Avg`/`Count` with a `Q(reviews__is_hidden=False)` filter in the same query as the products. The average is `None` when a product has no reviews. (2) Catalog cards show "★ 4.7 (3)" (`floatformat:1`, matching the product page) or "No reviews yet". (3) A query-count test checks that adding five tagged, reviewed products leaves the catalog's query count unchanged. `CatalogView` applies `with_ratings()`, and `CategoryView` inherits it. Ordinary tests cover category pages showing the same rating and hidden reviews being left off cards. Six new tests in all. The full suite passed (343), and `ruff check` and `ruff format` were clean. Nothing was committed.
- **Deviations:** No recommendation was overridden, and the user asked no follow-up questions. Behavior 3 passed on its first run: the single-query annotation from behavior 1 already kept the count flat, so it never had a RED step. To show the test could fail, the assistant temporarily switched the card to `product.reviews.count`. The test then failed with `11 == 6`, and the template was restored. The user chose to keep it as a regression guard. The user asked for this entry before confirming the browser check that the `implement` skill asks for, so this log does not record a manual verification of the phase.
- **Sideways:** Behavior 1 needed a placeholder `with_ratings()` that returned constant `None`/0 so that RED failed on an assertion rather than an `AttributeError`. The first version of the card split the rating and the count into separate spans, so the literal "★ 4.7 (3)" never appeared in the page. They were merged into one span before the test passed. That test then raised `UnorderedObjectListWarning`: aggregate annotations stop Django from applying `Meta.ordering`, so pagination would have had no stable order. The fix was an explicit `.order_by("name")` in `CatalogView`, with a comment. A combined test run went past the 2-minute tool timeout and finished in the background (it passed).

## 2026-10-17 — Product Reviews Phase 3: delete your review (TDD)

### Prompts
1. `/implement @prd/product-reviews.md @plans/product-reviews.md implement phase 3`
2. Yes, I approve these two behaviors. Go ahead and write the tests.
3. Yes I approve
4. Yes, move on to behavior 2
5. Yes I approve
6. Yes continue with phase 3
7. How can I manually verify this phase in the browser?
8. Yes everything passes

### Summary
- **Outcome:** Implemented Phase 3 of `plans/product-reviews.md` (user stories 19, 20) through the `implement` skill, which delegated two behaviors to `tdd`. (1) Confirming a delete removes the review and redirects to the product page with "Done — your review is deleted." (2) Someone else's review returns 403 on both GET and POST and the review survives. Each was shown RED on an assertion and approved before the code was written. `ReviewDeleteView` (`DeleteView` + `UserPassesTestMixin`, ownership as the test) lives at `/reviews/<pk>/delete/` (`reviews:delete`). The URL is pk-keyed rather than slug-keyed so "someone else's review" is expressible, and non-owners get 403 rather than a 404 from a filtered queryset. Anonymous users are sent to sign in. A new `review_confirm_delete.html` shows the review's stars and comment with "Keep my review" and "Delete review" buttons. The author's pinned review card gained a Delete link. Normal tests cover the confirmation page, the anonymous redirect, an unknown pk (404), the Delete link appearing only for the author, and writing a fresh review after deleting (the product page flips back to "Write a review"). `ruff` is clean, the full suite is green, and the user verified the phase in the browser. Nothing was committed.
- **Deviations:** No recommendation was overridden. The assistant proposed only two TDD behaviors instead of three, because "write again after deleting" was already handled by `can_create` and would have passed on its first run; it got a normal test instead. Blocking deletion of *hidden* reviews was left to Phase 7, where the plan puts it, so a hidden review is still deletable by its author until then (it isn't shown to them, so there's no link). This entry was written as step 5 of the `implement` skill rather than after the file's standard prompt. Prompt 7 was a follow-up asking how to verify the phase by hand.
- **Sideways:** Behavior 1 first failed with `NoReverseMatch`, so a URL and a placeholder view were added before RED. Behavior 2's GET case first failed with `TemplateDoesNotExist`, so the real confirmation template was written as scaffolding before RED. Editing `reviews/views.py` with a Python script on Windows wrote it as cp1252, turning the new em dash into an invalid byte and breaking 25 tests with a `SyntaxError` on import; the byte was rewritten as UTF-8 and the diff confirmed no other text changed. The full suite ran in the background (several minutes on this machine). The assistant did not open the pages in a browser itself; the user did.

## 2026-10-17 — Product Reviews Phase 2: edit your review (TDD)

### Prompts
1. `/tdd @prd/product-reviews.md @plans/product-reviews.md implement phase 2`
2. Yes, I approve these three behaviors and agree with using a 60-second threshold for the edited marker.
3. Yes, I approve this test. Go ahead and write the code to make it pass.
4. Let's keep Behavior 2 as a regression guard and move on.
5. Yes approved, write the code to make it pass.
6. Yes, go ahead with Phase 2.
7. How can I manually verify this phase in the browser?
8. Update PROMPTS.md with the standard prompt for completing phase 2

### Summary
- **Outcome:** Implemented Phase 2 of `plans/product-reviews.md` (user stories 6, 14, 16, 17, 18) using the `tdd` skill for three approved behaviors. (1) The write URL edits an existing review in place. `ReviewWriteView` became an `UpdateView` whose object is the user's existing review, or `None` for the create form. Its `test_func` passes owners through and falls back to `can_create` for everyone else, and the success message reads "Thanks — your review is updated." for edits. (2) Editing still works after the order is cancelled, because ownership alone gates editing. (3) `Review.edited` is true only when `updated_at` is more than 60 seconds after `created_at` (an `EDIT_GRACE` module constant, strict `>`). Each was shown RED with an approved test before the code was written. The rest of the phase was built with normal tests. The edit form says "Edit your review of …" with a "Save changes" button and opens prefilled. The product page says "Edit your review" instead of "Write a review" for a customer who already reviewed the product. A new `_review_card.html` partial shows "· edited" beside the date on edited reviews. `ProductDetailView` passes the viewer's own visible review as `own_review`, pinned first with a "Your review" badge and left out of the list below. The full suite is green (328 passed) and `ruff` is clean. Nothing was committed.
- **Deviations:** No recommendation was overridden. The user approved the three proposed behaviors and the suggested 60-second threshold, and kept behavior 2 as a regression guard after the assistant pointed out that behavior 1's change would make it pass immediately. The assistant chose the "updated" success wording and showed it for review with the test. It limited the pinned review to visible reviews and left the author's hidden-review view to Phase 7, so for now a customer whose review is hidden sees neither the review nor an Edit button. Prompt 7 was a follow-up asking how to verify the phase by hand. The answer used the seeded `customer` and `employee` logins: write a MindSync review, wait over a minute and edit it to see the "edited" marker, cancel the order from the back office and edit again, check the pages that should stay unchanged, and add a review from another user in the Django shell to see the pin.
- **Sideways:** Behavior 1's first run failed with an `IndexError` on an empty redirect chain rather than an assertion. That was fixed mechanically by asserting on the whole redirect chain, so RED was a real assertion failure. Behavior 2 passed on its first run because behavior 1 had already implemented it. To show it still guards something, the assistant temporarily removed the ownership check, watched the test fail with 403, and restored the view. Behavior 3 first failed with an `AttributeError`, so a placeholder property returning False was added before showing RED. Ruff reformatted `reviews/tests.py`. The assistant did not open the pages in a browser itself; verification was by tests only.

## 2026-10-17 — Product Reviews Phase 1: write a review and see it on the product page

### Prompts
1. `@prd/product-reviews.md @plans/product-reviews.md Implement phase 1`
2. How can I manually verify this phase in the browser?
3. Update PROMPTS.md with the standard prompt for completing Phase 1.

### Summary
- **Outcome:** Implemented Phase 1 of `plans/product-reviews.md` (user stories 3, 4, 5, 7, 8, 9, 11, 12, 13, 15). A new `reviews` app follows the `coupons` precedent and is registered in settings and the root URLconf. The `Review` model has `user` and `product` FKs (both `CASCADE`), a 1–5 `rating` enforced by validators, a required `comment`, `is_hidden`, `created_at` defaulting to now (so the seed can backdate) and `updated_at` with `auto_now`. It also has a `(user, product)` `UniqueConstraint` and newest-first ordering, and one migration creates it. `ReviewQuerySet` gained `visible()` and a `rating_summary()` aggregate (average and count). `ReviewManager.can_create(user, product)` is the single eligibility rule: signed in, not staff, an order line for the product in a `DELIVERED` order, and no existing review. `ReviewForm` declares a 1–5 `TypedChoiceField` rendered as DaisyUI star radios and a `CharField(min_length=20)` comment with a friendly error. The minimum is measured after trimming, so whitespace padding doesn't count. `ReviewWriteView` at `/products/<slug>/review/` (`reviews:write`) uses `UserPassesTestMixin` with `can_create`, so anonymous users are sent to sign in and ineligible users get 403. On success it redirects to the product page with "Thanks — your review is live." `ProductDetailView` now passes the visible reviews, the rating summary and `can_review` to the page. The product page has a new reviews section with the average and count, a "Write a review" button for eligible customers only, review cards (stars, comment, author, date) and a designed "No reviews yet" empty state. `conftest.py` gained a `make_order(user, product, status)` helper and `delivered_order` and `review` fixtures. `CLAUDE.md`'s project layout gained a `reviews/` entry. `reviews/tests.py` covers eligibility, the model's rules, the form, the write view and the product page. The full suite is green (316 passed) and `ruff` is clean. The migration was also applied to the dev database. Nothing was committed.
- **Deviations:** No recommendation was overridden. The assistant made three calls the plan left open: a "Verified buyer" badge on every review card (for user story 7), the `rating_summary()` queryset method, and a `make_order` helper in `conftest.py` that builds orders directly at a given status instead of going through checkout. Until Phase 2, a customer who already reviewed a product gets 403 on the write URL. Prompt 2 was a follow-up asking how to verify the phase by hand. The answer walked through the empty state signed out, the sign-in redirect, writing a review as `customer` (including the short and whitespace-padded comment errors), adding a second review in `/admin/` to see the average and newest-first order, the 403s for shipped and placed orders and for staff, and hiding a review in `/admin/`. It used the existing seeded orders, since the seed creates no reviews until Phase 9.
- **Sideways:** The first `pytest` run went past the two-minute tool timeout and finished in the background (about 3.5 minutes). The assistant's first wait loop matched ruff's "All checks passed!" instead of pytest's summary and reported finished early. A second loop that matched only the "N passed" line read the real result. Ruff reformatted two of the new files. To keep the newest-first tests reliable, they set `created_at` explicitly, because two reviews created back to back can share a timestamp on Windows. The assistant did not open the pages in a browser itself; verification was by tests only.

## 2026-10-11 — Account Security Center Phase 6: sign-in lockout and reset-email rate limit

### Prompts
1. `@prd/account-security-center.md @plans/account-security-center.md Do Phase 6.`
2. How can I manually verify this phase in the browser?
3. Update PROMPTS.md with the standard prompt.

### Summary
- **Outcome:** Implemented Phase 6 of `plans/account-security-center.md` (user stories 26–32). `accounts/security.py` gained the two cache-backed throttles. The login throttle is `login_allowed`, `record_login_failure` and `clear_login_failures`. It counts per username and IP under hashed cache keys: 5 failures in a 15-minute window lock the pair out for 15 minutes, and the count starts from zero once the lockout lifts. The reset throttle is `allow_reset_email`, which allows 3 emails per address per hour, ignoring case. Both use fixed windows that open with the first counted event. In `accounts/forms.py`, a shared `LoginThrottleMixin` refuses a locked-out pair before checking the password ("Too many attempts — try again in 15 minutes."). It records any failed sign-in and clears the count on success. The mixin is applied to `SignInForm` and to a new `AdminSignInForm`. `AdminSignInForm` extends Django's `AdminAuthenticationForm`, so non-staff are still turned away. `accounts/admin.py` sets `admin.site.login_form` to it. `StyledPasswordResetForm` overrides `send_mail` to skip over-limit emails silently, so the response is unchanged. `conftest.py` gained an autouse `clear_cache` fixture. Thirteen new tests cover the security module directly (lockout on the fifth failure, per-pair counts, clearing, lockout expiry and the reset limit with its expiry; expiry tests move `time.time` forward). They also cover the storefront lockout on the sixth attempt with the correct password, another IP not locking out the owner, success resetting the count, the admin lockout, admin still rejecting non-staff and admitting staff, and a fourth reset request sending nothing but returning an identical response. The full suite is green (275 passed) and `ruff` is clean. Nothing was committed.
- **Deviations:** No recommendation was overridden. The assistant made three calls the plan left open. A non-staff user with a correct password at `/admin/` counts as a failed sign-in. Reset requests for unknown emails aren't counted, since nothing is sent. The storefront and admin logins share one counter per username and IP. Prompt 2 was a follow-up asking how to verify the phase by hand. The answer walked through the storefront lockout, the lockout being per username, success clearing the count, the admin lockout and non-staff rejection, and the reset-email limit as seen in the `runserver` terminal. It noted that any server restart, including auto-reload, clears the in-memory counters. It also noted that the "different IP" case can't easily be shown from one browser and is covered by a test.
- **Sideways:** A heredoc used to edit `accounts/security.py` turned an intended `\0` separator in the cache-key f-string into a literal NUL byte. A follow-up `grep` reported the file as binary, which caught it. The byte was replaced with a `|` separator, which can't appear in a valid username or an IP address, before any tests ran. The full suite takes about three minutes to run.

## 2026-10-11 — Account Security Center Phase 5: the forgot-password loop

### Prompts
1. `@prd/account-security-center.md @plans/account-security-center.md Do Phase 5.`
2. How can I manually verify this phase in the browser?
3. Update PROMPTS.md with the standard prompt.

### Summary
- **Outcome:** Implemented Phase 5 of `plans/account-security-center.md` (user stories 4–12, 24, 34). The sign-in page gained a "Forgot password?" link. Three views are built on Django's stock reset views. `RequestPasswordResetView` at `/accounts/password/reset/` (`accounts:password_reset`) uses a new `StyledPasswordResetForm`. `PasswordResetSentView` at `/accounts/password/reset/sent/` (`accounts:password_reset_done`) shows the generic "If an account exists for that email…" message, the link lifetime and a spam hint. `ChooseNewPasswordView` at `/accounts/password/reset/<uidb64>/<token>/` (`accounts:password_reset_confirm`) uses a new `StyledSetPasswordForm`. It shows a "This link doesn't work" state with a "Request a new link" button for invalid, expired or used links. On success it sends the alert and redirects to sign-in with "Your password has been reset — sign in with your new password." It doesn't sign the user in. The plain-text reset email and its subject live in `templates/accounts/email/`. The link lifetime shown on the done page and in the email comes from `PASSWORD_RESET_TIMEOUT` through a small `_reset_link_lifetime()` helper in the views. `accounts/security.py` gained a public `send_password_reset_alert(user, request) -> bool` with the template `password_reset_completed.txt`. The shared alert context gained a `reset_url`. `PASSWORD_RESET_TIMEOUT` reads from `.env` with a default of 3600 and is documented in `.env.example`. Thirteen new tests cover the login link, identical responses for known and unknown emails, case-insensitive matching, the done-page wording, the email link, the password validators, the completed reset handing off to sign-in, other sessions being signed out, the alert, used links, expired links and the setting's default. The expired-link test overrides the timeout to 60 seconds and moves the token generator's clock forward. The full suite is green (262 passed) and `ruff` is clean. Nothing was committed.
- **Deviations:** No recommendation was overridden. The plan's URL list names four reset pages (request, done, confirm, complete), but the PRD says completion redirects to sign-in with a success message. The assistant followed the PRD, so there is no separate "complete" page and only three of Django's four reset views are wired. It left the Phase 3 and Phase 4 alert templates unchanged; only the new alert uses `reset_url`. Prompt 2 was a follow-up asking how to verify the phase by hand. The answer walked through the request page with known, unknown, differently capitalized and background-customer emails; a private window signed in as `customer` to show other sessions being signed out; the validator errors; the success message and the alert in the `runserver` terminal; the used-link and expired-link states (via `PASSWORD_RESET_TIMEOUT=60` in `.env`); and re-running `seed` afterward, since the committed `db.sqlite3` changes.
- **Sideways:** The first full test run had three failures. Two came from Django's `timeuntil`, which joins "1 hour" with a non-breaking space; the helper now swaps in an ordinary space so the plain-text email reads cleanly. The third came from the known-vs-unknown comparison, which failed because `base.html` renders a freshly masked CSRF token on every response; the test now blanks the token before comparing. The first `pytest` run went past the two-minute tool timeout and finished in the background. The assistant did not open the pages in a browser itself; verification was by tests only.

## 2026-10-11 — Account Security Center Phase 4: change email, with its alert

### Prompts
1. `@prd/account-security-center.md @plans/account-security-center.md Do Phase 4.`
2. How can I manually verify this phase in the browser?
3. Update PROMPTS.md with the standard prompt.

### Summary
- **Outcome:** Implemented Phase 4 of `plans/account-security-center.md` (user stories 16, 17, 18, 21). `accounts/security.py` gained a public `send_email_changed_alert(user, old_email, request) -> bool`. It sends to the *old* address and skips the send when there was no previous email or the address didn't change. The private `_send_alert` helper now takes an explicit `recipient`; the Phase 3 password alert passes `user.email`, so its behavior is unchanged. The new alert body is `templates/accounts/email/email_changed.txt`. It names the new address and the time, and says to sign in and change the email and password, or contact support, if the change wasn't theirs. A new `EmailChangeForm` (a plain form taking the user) validates the current password and applies `User.objects.email_in_use(..., exclude_pk=user.pk)`, so re-entering one's own address is allowed. A new `ChangeEmailView` (`LoginRequiredMixin` + `SuccessMessageMixin` + `FormView`) at `/accounts/security/email/` (`accounts:email_change`) renders `templates/accounts/email_change.html`. On success it saves the email, sends the alert, and redirects to the hub with "Your email has been updated." The hub gained a "Change email" / "Add email" button, and the missing-email warning gained an "Add an email" button. Eight new tests cover the anonymous redirect, the hub link, a wrong password, a duplicate email in different capitalization, re-entering one's own email, normalization with the redirect and message, the alert going to the old address only, and adding a first email (no alert, warning cleared). The full suite is green (249 passed) and `ruff` is clean. Nothing was committed.
- **Deviations:** No recommendation was overridden. The assistant chose a plain `forms.Form` over a `ModelForm` because a `ModelForm` would change the signed-in user's in-memory email on a failed submission. It flagged that including the new address in the alert is a judgment call, and that the alert doesn't point to "Forgot password?" because a reset would now go to the new address, which is worth revisiting in Phase 5. Prompt 2 was a follow-up asking how to verify the phase by hand. The answer walked through the seeded `customer`, `oldtimer`, `employee` and `admin` logins and checked the alert's recipient in the `runserver` terminal. It recommended re-running `seed` afterward, since the changes alter the committed `db.sqlite3`.
- **Sideways:** Nothing significant. `ruff format` reformatted two files once. The assistant did not open the pages in a browser itself; verification was by tests only.

## 2026-10-11 — Account Security Center Phase 3: change password, with its alert

### Prompts
1. `@prd/account-security-center.md @plans/account-security-center.md Do Phase 3.`
2. How can I manually verify this phase in the browser?
3. Update PROMPTS.md with the standard prompt.

### Summary
- **Outcome:** Implemented Phase 3 of `plans/account-security-center.md` (user stories 19, 20, 21, 23, 25, and 31 for alerts). The new module `accounts/security.py`, the third deliberate deep module, has a public `send_password_changed_alert(user, request) -> bool`, backed by a private `_send_alert` helper for the Phase 4 and 5 alerts to reuse. It sends nothing for accounts with no email. The alert body is the plain-text `templates/accounts/email/password_changed.txt`, which says what changed and when, and to use "Forgot password?" on the sign-in page (absolute link) if the change wasn't theirs. A new `ChangePasswordView` (Django's `PasswordChangeView` + `SuccessMessageMixin`) at `/accounts/security/password/` (`accounts:password_change`) uses a DaisyUI-styled `StyledPasswordChangeForm` and renders `templates/accounts/password_change.html`. It sends the alert after a successful change and redirects to the hub with "Your password has been changed." The hub gained a "Change password" button. `DEFAULT_FROM_EMAIL` is read from `.env` (default `ThoughtTronix <no-reply@thoughttronix.local>`) and documented in `.env.example`. `CLAUDE.md` now lists three deep modules. Ten new tests cover the anonymous redirect, the hub link, wrong-current, mismatched, and validator-failing passwords (no change, no stamp, no email), the success redirect and message, the current session surviving while a second client is signed out, the alert's recipient, sender, date and link, no alert without an email, and the setting's default. The full suite is green (241 passed) and `ruff` is clean. Nothing was committed.
- **Deviations:** No recommendation was overridden. This time the prompt's `@` paths were correct. The alert links to the sign-in page rather than a reset page, because the reset loop doesn't exist until Phase 5; the assistant flagged that Phase 5 could repoint it. Prompt 2 was a follow-up asking how to verify the phase by hand. The answer walked through the seeded `customer`, `oldtimer`, `employee` and `admin` logins, including a second browser to watch the other session get signed out. It warned that real password changes alter the committed `db.sqlite3` and recommended re-running `seed` afterward, which also rebuilds `media/products/`. It also flagged UTC times in the alert and Django's long password help text as things to check visually.
- **Sideways:** The first test run went past the shell's 120-second foreground timeout and was moved to the background. The assistant's first wait loop grepped for "passed", which matched ruff's "All checks passed!" and returned before pytest finished. A second loop waited for pytest's timing line instead and got the real result. `ruff format` reformatted the new tests once. The private helper's `changed_at` parameter was first written without a type hint and fixed right away.

## 2026-10-11 — Account Security Center Phase 2: the Security Center hub

### Prompts
1. `@prd/account-security.md @plans/account-security.md Do Phase 2.`
2. How can I manually verify this phase in the browser?
3. Update PROMPTS.md with the standard prompt.

### Summary
- **Outcome:** Implemented Phase 2 of `plans/account-security-center.md` (user stories 13, 14, 15, 22, 31 for the hub, and 33). A new `SecurityCenterView` (`LoginRequiredMixin` + `TemplateView`) at `/accounts/security/` (`accounts:security`) renders `templates/accounts/security.html`. The page shows username, email, last sign-in, member since, and password last changed: a date plus "N ago", or "Never changed since signup" when null. Blank-email accounts get a warning banner and a "No email on file" badge. In `base.html`, the navbar's "Hi, username" greeting became a DaisyUI `<details>` dropdown holding "Account security" and "Sign out", so it needs no JavaScript. `seed` gained a grandfathered `oldtimer` / `oldtimer123` customer with a blank email. It also writes backdated `password_changed_at` values directly after the passwords are set: `admin` 90 days ago, `employee` 21 days ago. Every other account stays null. The seed docstring and the README's demo-logins table list `oldtimer`. Seven new tests cover the anonymous redirect, access for customer, employee and admin, the displayed details, both password-changed states, the missing-email warning, and the navbar link for signed-in users only. The full suite is green (231 passed) and `ruff` is clean. Two back-to-back `seed` runs were checked on a scratchpad copy of `db.sqlite3` and gave identical results. Nothing was committed.
- **Deviations:** As in Phase 1, the prompt's `@` paths didn't exist, and the assistant used the `account-security-center.md` files and said so. No recommendation was overridden. Prompt 2 was a follow-up asking how to verify the phase by hand. The answer gave a per-login walkthrough (`customer`, `employee`, `admin`, `oldtimer`) and warned that `seed` rebuilds the committed `db.sqlite3` snapshot and `media/products/`. It also flagged two things for a visual check: the `<details>` dropdown may not close on an outside click, and times display in UTC.
- **Sideways:** Nothing failed during implementation. The plan describes a navbar "user menu", but the navbar had only a greeting and a Sign out button, so the assistant built the dropdown itself. Only the rendered HTML is tested, so its look and behavior depend on the manual browser check. When this entry was written, the working tree showed `db.sqlite3` modified and `media/products/ambientrest.png.jpg` deleted. Both came from the user running `seed` on the real database while verifying by hand. The deleted image is a previously uploaded product photo from the committed grading snapshot. `seed` wipes uploads, so it can be restored with `git restore` if the snapshot should keep it.

## 2026-10-11 — Account Security Center Phase 1: email at signup and the `User` model groundwork

### Prompts
1. `@prd/account-security.md @plans/account-security.md Do Phase 1.`
2. How can I manually verify this phase in the browser?
3. Append a session log to PROMPTS.md at the repo root, under today's date, newest entry at the top. Record every prompt I gave you this session, in order, including any corrections. End the entry with a short summary: the outcome, any places where I deviated from a recommended answer or asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** Implemented Phase 1 of `plans/account-security-center.md` (user stories 1–3). `accounts.User` gained a case-insensitive unique constraint on `email`, which skips blank emails so grandfathered accounts stay valid. It also gained email normalization (trim and lowercase) on save, a nullable `password_changed_at` field, and a `set_password()` override that stamps the field only for users that already have a primary key. A custom `UserManager.email_in_use(email, exclude_pk=None)` is ready for Phase 4's change-email form. One migration (`0002_email_unique_password_changed_at`) covers the manager, field, and constraint. `SignupForm` now requires an email and shows a friendly "An account with this email already exists." error. Existing signup tests were updated to send an email, and 11 new tests were added. The full suite is green (222 passed) and `ruff` is clean. The migration and two back-to-back `seed` runs were verified on a scratchpad copy of `db.sqlite3`, so the committed grading snapshot was not touched. Nothing was committed.
- **Deviations:** The prompt's `@` paths (`account-security.md`) didn't exist. The assistant used the actual files, `prd/account-security-center.md` and `plans/account-security-center.md`, and said so. It did not add a PROMPTS.md entry after Phase 1, because this file says entries are only added on request. Prompt 2 was a follow-up asking how to verify the phase by hand. The answer gave browser steps for signup, the duplicate-email error, and lowercase storage (checked in the admin user list). It noted that `password_changed_at` isn't visible in the browser until the Phase 2 hub, so that check uses the Django shell. It also noted that `migrate` modifies the committed `db.sqlite3` snapshot.
- **Sideways:** A Python string-replace script that edited `accounts/forms.py` silently failed to match. Windows Python read the file as cp1252, so the em-dash in the docstring didn't match. Only the import changes landed, and `ruff` caught them as unused imports. The form was then fixed with a direct edit, and a check of the diff found no corrupted characters. A combined lint and test command exceeded the 2-minute tool timeout because the suite takes about 2 minutes. It finished in the background and passed. One known edge was left open: if Django upgrades a password hash at sign-in, `set_password()` stamps the timestamp in memory, but Django saves only the `password` field, so the stamp isn't stored. This is harmless, and it was flagged to the user rather than guarded against.

## 2026-10-10 — Design an Account Security Center with `/grill-me`, then write its PRD with `/to-prd`

### Prompts
1. `/grill-me` (no plan given; the session had just been `/clear`ed).
2. I want to design an Account Security Center for ThoughtTronix. Customers should be able to provide an email address when they create an account, change their password, and reset a forgotten password through an email loop. Please recommend any other useful account security additions that fit this scope.
3. A. (Q1: email required at signup and unique ignoring case, enforced by a conditional database constraint; existing blank-email accounts grandfathered.)
4. A with the alert (Q2: email change requires the current password and saves immediately; alert sent to the old address.)
5. A (Q3: the reset form always shows the generic "If an account exists…" message.)
6. B (Q4: reset links expire after 1 hour.)
7. A (Q5: after a reset, send the user to the sign-in page instead of signing them in.)
8. B (Q6: alert emails on email change, password change, and completed reset.)
9. C and yes those numbers work for me (Q7: home-grown cache throttle, 5 failed logins per username + IP per 15 minutes, 3 reset emails per address per hour.)
10. A (Q8: Security Center hub page with separate email and password pages.)
11. B (Q9: add a nullable `password_changed_at`, stamped by a `User.set_password()` override.)
12. A (Q10: `accounts/security.py` becomes a third deliberate deep module; CLAUDE.md updated to match.)
13. A and yes admin login should go through the throttle too (Q11: the same rules for every role, and the Django admin login is throttled.)
14. B (Q12: seed adds a blank-email customer and backdates `password_changed_at` for one or two demo users.)
15. `/to-prd`
16. Append a session log to PROMPTS.md at the repo root, under today's date, newest entry at the top. Record every prompt I gave you this session, in order, including any corrections. End the entry with a short summary: the outcome, any places where I deviated from a recommended answer or asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** No application code changed. A 12-question `/grill-me` interview settled the Account Security Center design:
  - required, case-insensitive unique emails (blank ones grandfathered)
  - password-confirmed email change with an alert to the old address
  - Django's built-in password change and reset views, with a generic reset message, 1-hour single-use links (`PASSWORD_RESET_TIMEOUT` from `.env`), and sign-in required after a reset
  - alerts for email change, password change, and completed reset
  - a cache-based throttle on login (storefront and admin) and on reset emails
  - a `/accounts/security/` hub showing email, last sign-in, member since, and `password_changed_at`
  - `accounts/security.py` as a third deep module
  - seed additions so every hub state can be demoed

  Before asking anything, the assistant read the code to check the current state: `SignupForm` deliberately left email out, `User.email` was optional and not unique, seed users already had `@example.com` emails, and email used the console backend. `/to-prd` then wrote `prd/account-security-center.md` (34 user stories, implementation decisions, out of scope, testing decisions, demo notes). Nothing committed.
- **Deviations:** The user took the recommended option on every question; no recommendation was overridden. Three answers added something:
  - Q2 explicitly accepted the old-address alert that was part of the recommendation.
  - Q7 confirmed the proposed throttle numbers.
  - Q11 also answered the assistant's side question and agreed to throttle the Django admin login.

  The user asked no other follow-up questions. The closing summary listed four small defaults (email normalization, `DEFAULT_FROM_EMAIL`, plain-text email templates, a cache-clearing test fixture); the user went straight to `/to-prd` without objecting, so the PRD includes them. Q6 raised a conflict with CLAUDE.md's "exactly two deep modules" rule and deferred it, and Q10 settled it.
- **Sideways:** `/grill-me` arrived with no plan, because the context had just been cleared, so the first turn read `prd/`, `plans/`, and git history and asked the user what to grill instead of starting the interview. The PRD went slightly past the template and the interview:
  - It added a Testing Decisions section, which `/to-prd`'s template doesn't have, to match `prd/core-platform.md`.
  - It listed "self-service account deletion" as out of scope, though the interview never discussed it.

  The assistant pointed out both when it delivered the PRD. While writing this log, a first draft wrongly said the PRD names a "legacy_lou" seed user. That name was only an example in Q12 and isn't in the PRD, and the line was corrected before the log was handed over.

## 2026-10-04 — Implement product images from the HANDOFF.md design

### Prompts
1. `@HANDOFF.md Implement this feature` — build the product-images design agreed in an earlier `/grill-me` interview and recorded in `HANDOFF.md`.
2. Let's leave that file where it is just to be safe. (Answering whether to delete the unused `product-images/SyncRest GPT Text.png`.)
3. Write the entry to PROMPTS.md now.

### Summary
- **Outcome:** Added `Product.image` (`ImageField`, `upload_to="products/"`, optional, png/jpg/jpeg/webp only) with Pillow (`uv add pillow`) and migration `0004_product_image`. `ProductForm` gained the field, a DaisyUI `file-input` class, and `clean_image` (5 MB limit, "Image must be 5 MB or smaller."). Set `MEDIA_ROOT`/`MEDIA_URL`, serve media in DEBUG via `static()` in `config/urls.py`, and gitignored `media/`. Added `Product.display_image_url` (the upload, or the category placeholder); the catalog cards (fixed 4:3, `object-cover object-top`) and the detail page use it. The back-office edit form got `enctype="multipart/form-data"` and a current-image thumbnail; Django's Clear checkbox brings back the placeholder. Moved 12 sample photos into `products/seed_images/<slug>.png`; `seed` wipes `media/products/` and attaches them, and reseeding twice left exactly 12 files. Added an autouse `MEDIA_ROOT = tmp_path` fixture, `png_upload`/`product_with_image` fixtures, and 10 tests. All 212 tests pass and ruff is clean. On the dev server, the catalog showed 12 photos and 22 placeholders, and the media URL served the PNG. Updated `CLAUDE.md`. Nothing committed.
- **Deviations:** One change beyond the handoff. Probing showed a `.txt` upload never got the agreed allowed-formats message: text content hit Pillow's "Upload a valid image" error first, and image bytes renamed `.txt` hit Django's form validator, which lists ~70 Pillow formats. Added a small `ProductImageField` (via `Meta.field_classes`) that checks the extension before Pillow, sharing one `validate_image_extension` with the model. On prompt 2, the user chose to keep the leftover `SyncRest GPT Text.png` rather than delete it. The handoff asked for this log entry, but this file's rule says entries are added only when prompted, so the assistant waited for prompt 3.
- **Sideways:** A scripted Python edit read files as cp1252, so two replacements containing an em dash silently didn't match. `makemigrations` then failed with `NameError: FileExtensionValidator`, and the two blocks were fixed by hand. Shell escaping put a literal null byte in the oversized-file test, which broke pytest collection. The first byte fix hit the same escaping problem, so the padding was changed to `b"x"`. `ruff format .` also re-wrapped one unrelated, already unformatted line in `orders/services.py`. `HANDOFF.md` said `product-images/` was untracked, but it was tracked, so the moves show as git deletions. The catalog's visual layout was checked over HTTP and the Tailwind build, not in a browser.

## 2026-10-04 — Design product images with `/grill-me`, then hand off with `/handoff`

### Prompts
1. `/grill-me` I need to add real product images to our catalog. Every product needs to show an uploaded image if we have one, or stick to the placeholder if it's missing. Employees should be able to upload images through the back office, but we need to reject wrong file types with a clear warning. The sample images are inside the product-images directory.
2. I want to go with option C. Let's allow png, jpg, jpeg, and webp formats so employees get a error message if they upload anything else.
3. Let's go with Option B. 
4. Option B sounds good. 
5. I agree with your recommendation. 
6. Let's go with Option B. 
7. Let's go with Option A. 
8. Let's go with Option A. 
9. Let's use Option A with object-top. 

### Summary
- **Outcome:** No code changed. An eight-question `/grill-me` interview settled the product-images design: `ImageField` plus an allowed-extensions list (png/jpg/jpeg/webp), a 5 MB limit in `ProductForm.clean_image`, `MEDIA_ROOT`/`MEDIA_URL` with DEBUG serving, one `Product.display_image_url` property for the placeholder fallback, 4:3 `object-cover object-top` catalog cards with the full image on the detail page, a back-office thumbnail plus Django's Clear checkbox, slug-named seed images in `products/seed_images/` that `seed` attaches after clearing `media/products/`, and an autouse `MEDIA_ROOT = tmp_path` test fixture. The assistant looked at the ambiguous images to map them: 12 of the 13 sample PNGs mapped to products, and the SyncRest "Text" poster was left out. Exploring the code also turned up the missing `enctype="multipart/form-data"` on the product form and the 4:3 vs 4:5 shape mismatch. `/handoff` then wrote `HANDOFF.md` at the repo root with the decisions, the filename-to-slug table, the test list, and finish-line checks, which the next session implemented.
- **Deviations:** On Q6 the user overrode the recommendation (B, delete old files on replace/clear/delete) and chose A, Django's default, because `seed` already wipes uploads. All other answers took the recommended option, and Q1 named the allowed formats. The assistant's closing question (implement now, or write `plans/product-images.md` first) was never answered. The design's "bookkeeping" line said to append a `PROMPTS.md` entry, which conflicts with this file's prompted-only rule; the next session waited to be asked.
- **Sideways:** On prompt 10 the assistant started building a new personal `/handoff` skill with the skill-creator before checking that the project already had one in `.claude/skills/handoff/`. The user rejected its first setup question, ran the existing `/handoff` directly, and the half-started personal skill was dropped. The interview's placeholder counts disagreed with each other ("the other 22 products" in Q4, "the other 23" in the final design); the next session's dev server showed 22.

## 2026-09-23 — Add a marketing-managed discount coupon feature

### Prompts
1. Requested the "grill-me" skill be run, then described a discount coupon feature for ThoughtTronix: marketing needs to create and retire codes without engineering help; codes must support both order-wide and product-specific discounts; expired codes must show a clean checkout error instead of breaking; retiring a code cannot change past orders. Specified design choices: codes are simple words like "FALL26"; codes can be used only once per customer; discounts are percentage-based (e.g., "20% off").
2. Answered three clarifying questions (asked via the question tool) about implementation details left open by the request: a product-specific coupon should discount only that product's line(s) in a mixed cart, not require the whole cart to match; "once per customer" should be enforced per logged-in account, not by guest email; coupons should be managed through a back-office CRUD screen rather than Django admin. All three recommended options were accepted.
3. Approved the implementation plan presented for the feature.
4. `pytest`
5. Requested this session log be appended to `PROMPTS.md`.

### Summary
- **Outcome:** Built a new `coupons` app (`Coupon` model with `code`, `percent_off`, optional `product` FK for scoping, `is_active`, `expires_at`; back-office list/create/edit/retire views — no delete, so history stays explainable) plus a "Coupons" tab in the staff shell. Wired coupons into `orders`: `Cart.coupon_code` and `Order.coupon_code`/`discount_amount` (the latter snapshotted at checkout so retiring or deleting a coupon never touches past orders), a single `resolve_coupon` function in `orders/services.py` reused by the cart's "Apply" action, checkout's pre-check, and `place_order`'s transactional backstop, and `compute_discount` for order-wide vs. product-specific math. Added demo coupons to `seed.py`. Added ~30 new/updated tests across `coupons/` and `orders/`; full suite green (202 passed), `ruff check`/`format` clean. Verified live against the running dev server (not just tests): applied a coupon on the cart page, watched the discount preview update, confirmed checkout's subtotal/discount/total, then retired the coupon in the back office and confirmed checkout showed a clean "retired" message instead of a crash.
- **Deviations:** The requested "grill-me" skill does not exist in this installation (not in the available-skills listing, and not found in the project's or user's skill/plugin directories); the assistant told the user and proceeded with direct exploration, clarifying questions, and a written plan instead. Separately, exploration of the codebase surfaced an existing test (`test_the_form_declares_no_imperative_validation`) asserting `CheckoutForm` has no imperative validation methods, a deliberate "declarative rules only" contract per the PRD — this reshaped the design mid-exploration (before any plan was shown to the user) from validating the coupon code as a `CheckoutForm` field to applying it on the cart page instead, so the checkout form itself stays untouched. The user did not override any recommendation; all three clarifying-question answers and the plan were accepted as proposed.
- **Sideways:** Two test failures surfaced on the first full `pytest` run and were fixed immediately: (1) a back-office coupon-creation test asserted a new coupon was active, but the create form's `is_active` checkbox was omitted from the POST payload, so Django (correctly) treated it as unchecked — fixed by adding `"is_active": "on"` to the test's default payload, matching the same pattern already used for `Product.is_available` elsewhere in the suite; (2) a view test asserted the literal string "isn't recognized" appeared in rendered HTML, but Django's autoescaping renders the apostrophe as an HTML entity — fixed by asserting on "recognized" instead. Both were caught by the test suite itself, not by manual testing.

## 2026-09-19 — Add `is_featured` to Product, badge it in templates, recover admin access

### Prompts
1. Look at the Product model in `products/models.py` and add a new boolean field named `is_featured`. It should default to `False` so existing products stay unfeatured. Do not add any badges or modify templates yet.
2. Please generate the database migration files for the products app and apply them to the database.
3. Please update the frontend templates to display a "Featured" badge for any product where `is_featured` is `True`. The badge must appear in two places: on the main catalog listing page and on the individual product detail page. Match the existing styling patterns used in the templates.
4. `uv run python manage.py tailwind runserver`
5. I am locked out of the Django admin panel at `/admin/`. Can you list the usernames of the superusers or staff accounts currently in the database? If there isn't one I can use, please create a new superuser with the username `admin` and password `admin123`.
6. The `/admin/` web interface is not loading correctly. Can you use a Django shell command or python script to programmatically set `is_featured=True` for the three products: `Seraphine`, `SoulSear Mark II`, and `SoulSear Mark I` and save them directly to the database?
7. Append a session log to `PROMPTS.md` at the repo root, under today's date, newest entry at the top. Record every prompt I gave you this session, in order, including any corrections.

### Summary
- **Outcome:** Added `Product.is_featured` (`BooleanField`, `default=False`) in `products/models.py`; generated and applied migration `products/migrations/0003_product_is_featured.py`. Added a "Featured" badge (`badge-primary badge-outline`, matching existing badge conventions) to `templates/products/catalog.html` and `templates/products/detail.html`, shown only when `product.is_featured` is true. Started the Tailwind dev server in the background. Set `is_featured=True` on Seraphine, SoulSear Mark I, and SoulSear Mark II via a Django shell one-off script (bypassing the broken `/admin/` UI), matched by exact product name and saved with `update_fields=['is_featured']`.
- **Deviations:** On prompt 5, a superuser named `admin` already existed in the database, so the assistant did not create a new one as literally requested — it surfaced the existing `admin` (superuser) and `employee` (staff) accounts instead and asked how to proceed (reset `admin`'s password to `admin123`, reset to a different password, or do nothing). The user chose to do nothing, so no credentials were changed and the original admin lockout was not resolved.
- **Sideways:** The admin lockout from prompt 5 was never actually fixed — the user declined all offered remedies, so whoever is locked out of `/admin/` still is. The `is_featured` flags on the three named products were set directly via shell script as a workaround for the same broken `/admin/` UI, rather than through the admin panel or a form.
