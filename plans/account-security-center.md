# Plan: The ThoughtTronix Store — Account Security Center

> Source PRD: `prd/account-security-center.md`. The PRD owns the requirements; this plan owns the sequence. Where a phase says "per the PRD," the PRD's wording is authoritative.

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: `accounts`, for everything. No new app.
- **URLs**: every URL is named under the `accounts` namespace. Security Center pages live under `/accounts/security/` (the hub, change email, change password). The password-reset pages (request, done, confirm, complete) live under `/accounts/`. The admin login keeps its URL; `admin.site` is configured to use a throttled sign-in form.
- **Models**: no new models. `accounts.User` gains:
  - a database-level conditional unique constraint on `email`, case-insensitive, applying only to non-blank values (blank emails stay valid for existing accounts);
  - email normalization on save (trimmed, lowercased);
  - a nullable `password_changed_at` timestamp (null = "Never changed since signup");
  - a `set_password()` override that stamps `password_changed_at` only for users that already have a primary key.
  - One migration covers the constraint and the new field.
- **Security module**: a new service module in `accounts` is the third deliberate deep module. It holds the login throttle, the reset-email throttle, and the security-alert senders, with docstrings and type hints on every public function. `CLAUDE.md` is updated from "exactly two" deep modules to three, naming it.
- **Auth/authorization**: Security Center pages are login-required and open to every role (customer, employee, admin). Password change and reset are built on Django's stock views and token generator. Throttling happens in forms, never in views; views call the security module only to send alerts.
- **Throttle storage**: Django's default in-memory cache. Login lockout: 5 failures per 15 minutes per username + IP, lasting 15 minutes. Reset email: 3 per hour per address.
- **Email**: console backend only. Email bodies (the reset email and three alerts) are plain-text templates in an `email` subfolder of the accounts templates. Each alert says what changed, when, and links to password reset.
- **Settings**: `DEFAULT_FROM_EMAIL` (default `ThoughtTronix <no-reply@thoughttronix.local>`) and `PASSWORD_RESET_TIMEOUT` (default 3600) are read from `.env` via environs and documented in `.env.example`; the app still runs with no `.env`.
- **Templates**: all new pages extend the project-level `base.html`. No HTMX partials. Forms carry DaisyUI widget classes like the existing signup and sign-in forms.

---

## Phase 1: Email at signup, and the model groundwork

**User stories**: 1, 2, 3

### What to build

Lay the `User` model foundation that every later phase relies on, and make signup collect an email. One migration adds the case-insensitive conditional unique constraint on `email` and the nullable `password_changed_at` field. Emails are normalized on save. `set_password()` stamps `password_changed_at` for existing users but not on creation. The signup form gains a required email field with a friendly "an account with this email already exists" error. The database constraint is still the real guarantee.

### Acceptance criteria

- [ ] Signing up requires an email; the new account stores it trimmed and lowercased.
- [ ] Signing up with an email already in use (in any capitalization) re-renders the form with a friendly duplicate error.
- [ ] The database rejects two accounts whose emails differ only by case, and still allows multiple accounts with blank emails.
- [ ] Creating a user leaves `password_changed_at` null; calling `set_password()` on a saved user stamps it.
- [ ] Existing users, fixtures, and the seed command keep working; the full suite is green.

---

## Phase 2: Security Center hub

**User stories**: 13, 14, 15, 22, 31 (hub), 33

### What to build

A login-required hub at `/accounts/security/`, reached from a new "Account security" entry in the navbar user menu. It shows the account's email, last sign-in, member-since date, and when the password was last changed ("Never changed since signup" when null). Accounts with no email see a prominent warning that they can't be recovered until they add one. The seed command adds a grandfathered customer with a blank email and backdates `password_changed_at` for one or two demo users, writing the value directly after the password is set. Every other demo user keeps a null value. With the seed alone, a grader can see every state of the hub.

### Acceptance criteria

- [ ] Anonymous visitors are redirected to sign-in; customers, employees, and the admin all reach the hub.
- [ ] The hub shows email, last sign-in, member since, and password last changed, including the "Never changed since signup" state.
- [ ] An account with a blank email sees the missing-email warning instead of an address.
- [ ] The navbar user menu shows "Account security" to signed-in users only.
- [ ] After seeding, the grandfathered no-email customer and the backdated password-change users exist; seed stays idempotent.

---

## Phase 3: Change password, with its alert

**User stories**: 19, 20, 21, 23, 25, 31 (alerts)

### What to build

A change-password page under `/accounts/security/`, built on Django's password-change view and form, styled with DaisyUI. The user enters their current password and the new one twice. On success the current session stays signed in and every other session is invalidated. The password-changed alert is sent, and the user returns to the hub with a success message. The page also shows the updated "password last changed." This phase creates the security module with its first alert function and plain-text email template. It adds the `DEFAULT_FROM_EMAIL` setting and updates `CLAUDE.md` to list three deep modules.

### Acceptance criteria

- [ ] A wrong current password, mismatched new passwords, or a password that fails the validators each re-render the form with errors.
- [ ] A successful change keeps the current session signed in and signs out the user's other sessions.
- [ ] A successful change stamps `password_changed_at`, redirects to the hub, and shows a success message.
- [ ] One alert email goes to the user's address, saying what changed, when, and how to reset if it wasn't them. No alert is attempted for an account with no email.
- [ ] `DEFAULT_FROM_EMAIL` reads from `.env` with the documented default, and `.env.example` documents it.
- [ ] `CLAUDE.md` names the security module as the third deep module.

---

## Phase 4: Change email, with its alert

**User stories**: 16, 17, 18, 21

### What to build

A change-email page under `/accounts/security/` that takes the new email and the current password. The form validates the password against the signed-in user and applies the signup uniqueness rule, excluding the user's own account. On success the email updates immediately and the email-changed alert goes to the *previous* address, if there was one. The user then returns to the hub with a success message. A grandfathered user adds their first email the same way, which clears the missing-email warning.

### Acceptance criteria

- [ ] A wrong current password is rejected with a form error, and the email is unchanged.
- [ ] An email used by another account (in any capitalization) is rejected. Re-entering one's own email is not treated as a duplicate.
- [ ] A successful change stores the normalized new email, redirects to the hub, and shows a success message.
- [ ] The alert goes to the old address, not the new one. No alert is sent when the old email was blank.
- [ ] Anonymous visitors are redirected to sign-in.

---

## Phase 5: The forgot-password loop

**User stories**: 4, 5, 6, 7, 8, 9, 10, 11, 12, 24, 34

### What to build

The full email-driven reset loop, built on Django's four password-reset views and token generator. The sign-in page gains a "Forgot password?" link. The request page always shows the same "If an account exists for that email…" result. The done page states the one-hour expiry and suggests checking spam. The reset email (plain-text template) prints to the console with a working link. The confirm page enforces the signup password rules. For an invalid, expired, or used link, it shows a clear message with a link to request a new one. On success, other sessions are invalidated and the password-reset alert is sent. The user is redirected to sign-in with a success message and is not signed in automatically. The `PASSWORD_RESET_TIMEOUT` setting is added.

### Acceptance criteria

- [ ] The sign-in page links to the reset request page.
- [ ] Requests for a known and an unknown email produce identical responses. Only the known email receives a reset email.
- [ ] The reset email's link opens the confirm page and lets the user set a new password that meets the validators.
- [ ] Expired links (tested by overriding the timeout) and already-used links show the invalid-link message with a way to request a new one.
- [ ] Completion redirects to sign-in with a success message, the user is not signed in, other sessions are invalidated, and the reset alert is sent.
- [ ] `PASSWORD_RESET_TIMEOUT` reads from `.env`, defaults to 3600, and is documented in `.env.example`.

---

## Phase 6: Brute-force protection — sign-in lockout and reset-email rate limit

**User stories**: 26, 27, 28, 29, 30, 31 (lockout), 32

### What to build

Both cache-backed throttles go into the security module. The **login throttle** checks, records, and clears failures per username + IP pair: 5 failures in 15 minutes trigger a 15-minute lockout. A shared throttle mixin applies it to the storefront sign-in form and to a new admin sign-in form that extends Django's admin authentication form, which still enforces `is_staff`. `admin.site` uses the new form. A locked-out attempt shows "Too many attempts — try again in 15 minutes" even with the correct password, and a successful sign-in clears the count. The **reset-email throttle** allows at most 3 reset emails per address per hour. A reset form extending Django's stock form skips over-limit requests silently, so the response is identical to every other request. An autouse fixture in the project-level `conftest.py` clears the cache before each test.

### Acceptance criteria

- [ ] The security module, tested directly without HTTP: lockout after the fifth failure; separate counts per username + IP; clearing on success; lockout expiry; and the reset-email limit.
- [ ] The storefront sign-in shows the lockout message on the sixth attempt, even with the correct password. Failing from a different IP does not lock out the real owner.
- [ ] A successful sign-in before the limit resets the failure count.
- [ ] The Django admin login is throttled the same way and still rejects non-staff users.
- [ ] A fourth reset request for the same address within an hour sends no email but returns the same response as any other request.
- [ ] An autouse fixture clears the cache before every test, and the full suite is green.
