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

## 2026-10-04 — Implement product images from the HANDOFF.md design

### Prompts
1. `@HANDOFF.md Implement this feature` — build the product-images design agreed in an earlier `/grill-me` interview and recorded in `HANDOFF.md`.
2. Let's leave that file where it is just to be safe. (Answering whether to delete the unused `product-images/SyncRest GPT Text.png`.)
3. Write the entry to PROMPTS.md now.

### Summary
- **Outcome:** Added `Product.image` (`ImageField`, `upload_to="products/"`, optional, png/jpg/jpeg/webp only) with Pillow (`uv add pillow`) and migration `0004_product_image`. `ProductForm` gained the field, a DaisyUI `file-input` class, and `clean_image` (5 MB limit, "Image must be 5 MB or smaller."). Set `MEDIA_ROOT`/`MEDIA_URL`, serve media in DEBUG via `static()` in `config/urls.py`, and gitignored `media/`. Added `Product.display_image_url` (the upload, or the category placeholder); the catalog cards (fixed 4:3, `object-cover object-top`) and the detail page use it. The back-office edit form got `enctype="multipart/form-data"` and a current-image thumbnail; Django's Clear checkbox brings back the placeholder. Moved 12 sample photos into `products/seed_images/<slug>.png`; `seed` wipes `media/products/` and attaches them, and reseeding twice left exactly 12 files. Added an autouse `MEDIA_ROOT = tmp_path` fixture, `png_upload`/`product_with_image` fixtures, and 10 tests. All 212 tests pass and ruff is clean. On the dev server, the catalog showed 12 photos and 22 placeholders, and the media URL served the PNG. Updated `CLAUDE.md`. Nothing committed.
- **Deviations:** One change beyond the handoff. Probing showed a `.txt` upload never got the agreed allowed-formats message: text content hit Pillow's "Upload a valid image" error first, and image bytes renamed `.txt` hit Django's form validator, which lists ~70 Pillow formats. Added a small `ProductImageField` (via `Meta.field_classes`) that checks the extension before Pillow, sharing one `validate_image_extension` with the model. On prompt 2, the user chose to keep the leftover `SyncRest GPT Text.png` rather than delete it. The handoff asked for this log entry, but this file's rule says entries are added only when prompted, so the assistant waited for prompt 3.
- **Sideways:** A scripted Python edit read files as cp1252, so two replacements containing an em dash silently didn't match. `makemigrations` then failed with `NameError: FileExtensionValidator`, and the two blocks were fixed by hand. Shell escaping put a literal null byte in the oversized-file test, which broke pytest collection. The first byte fix hit the same escaping problem, so the padding was changed to `b"x"`. `ruff format .` also re-wrapped one unrelated, already unformatted line in `orders/services.py`. `HANDOFF.md` said `product-images/` was untracked, but it was tracked, so the moves show as git deletions. The catalog's visual layout was checked over HTTP and the Tailwind build, not in a browser.

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
