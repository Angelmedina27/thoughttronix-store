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
