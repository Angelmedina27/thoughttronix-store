# PRD: The ThoughtTronix Store — Account Security Center

*Commissioned by ThoughtTronix Product Management. "Your Thoughts, Our Business."*

---

## Problem Statement

A ThoughtTronix account holds a customer's order history, shipping addresses, and the standing ability to buy neural technology in their name. Today that account is protected by a username and a password — and nothing else.

Customers sign up without giving an email address, so there is no channel through which the store can reach them about their own account. A customer who forgets their password has no way back in: there is no "forgot password" link, and no address to send a reset to. A customer who wants to change their password cannot do it from the storefront at all. Nobody is told when an account's credentials change, so a customer whose account has been taken over finds out only when something goes wrong.

The sign-in form accepts unlimited attempts. A script can guess passwords against any username — including staff accounts that can see every order and the revenue dashboard — and nothing slows it down. The Django admin login has the same gap.

## Solution

An **Account Security Center**: a single page, reachable from the navbar's user menu, where any signed-in user can see the state of their account and change the credentials that protect it.

- **Email at signup.** New accounts must provide an email address, and no two accounts may share one (ignoring letter case). Accounts created before this feature keep working; the Security Center warns them that their account can't be recovered until they add an email.
- **Change email.** From the Security Center, with the current password as proof of identity. The *old* address is told about the change.
- **Change password.** From the Security Center, with the current password. The user stays signed in on the device they're using; every other session is signed out.
- **Forgot password.** A link on the sign-in page starts an email loop: enter an email, receive a one-hour, single-use reset link, choose a new password, sign in. The form never reveals whether an email has an account.
- **Security alerts.** An email goes out whenever an account's email or password changes, so the real owner learns of a takeover immediately.
- **Brute-force protection.** Repeated failed sign-ins are locked out for a while, on both the storefront and the admin login. Reset emails are rate-limited so the form can't be used to flood an inbox.

The Security Center hub shows the account's email (or the missing-email warning), last sign-in, member-since date, and when the password was last changed.

## User Stories

**Visitor (signing up)**

1. As a visitor, I want to provide my email address when I create an account, so that I can recover my account later if I forget my password.
2. As a visitor, I want to be told if the email I entered is already in use, so that I know to sign in or reset my password instead of creating a duplicate account.
3. As a visitor, I want `Bob@Example.com` and `bob@example.com` treated as the same address, so that a difference in capitalization can't split my identity across two accounts.

**Customer (forgot password)**

4. As a customer who has forgotten my password, I want a "Forgot password?" link on the sign-in page, so that I can start recovering my account.
5. As a customer, I want to enter my email and receive a password reset link, so that I can choose a new password without contacting anyone.
6. As a customer, I want the reset page to show the same message whether or not my email has an account, so that strangers can't use the form to discover who shops at ThoughtTronix.
7. As a customer, I want the confirmation page to tell me the link expires in one hour and to check my spam folder, so that I know what to expect and what to do if nothing arrives.
8. As a customer, I want my reset link to stop working after one hour or after it's been used, so that an old email sitting in my inbox can't be used against me.
9. As a customer, I want to see a clear message if my reset link is expired or invalid, with a way to request a new one, so that I'm not stuck.
10. As a customer, I want my new password checked against the same strength rules as signup, so that a reset can't weaken my account.
11. As a customer, I want to be sent to the sign-in page with a success message after resetting my password, so that I confirm my new password works and my password manager can save it.
12. As a customer, I want every other signed-in session on my account signed out when my password is reset, so that anyone who got into my account is kicked out.

**Customer (Security Center)**

13. As a signed-in customer, I want an "Account security" entry in the navbar's user menu, so that I can find my security settings.
14. As a signed-in customer, I want the Security Center to show my email, my last sign-in, when I joined, and when my password was last changed, so that I can spot activity I don't recognize.
15. As a customer who signed up before emails were collected, I want a prominent warning that my account has no email on file, so that I understand I can't recover it until I add one.
16. As a customer, I want to add or change my email by confirming my current password, so that someone using my unlocked computer can't redirect my account's recovery email.
17. As a customer, I want an alert sent to my *previous* email address when my email is changed, so that I find out if someone else changed it.
18. As a customer, I want my new email held to the same uniqueness rules as signup, so that I can't accidentally claim an address another account uses.
19. As a customer, I want to change my password by entering my current password and my new one twice, so that typos and stolen sessions can't change it.
20. As a customer, I want to stay signed in on my current device after changing my password, while my other sessions are signed out, so that changing my password is a fix rather than an inconvenience.
21. As a customer, I want to be returned to the Security Center with a success message after each change, so that I know it took effect.
22. As a customer, I want "Password last changed" to show "Never changed since signup" if I've never changed it, so that the hub is honest about what it knows.

**Customer (alerts)**

23. As a customer, I want an email when my password is changed, so that I find out immediately if it wasn't me.
24. As a customer, I want an email when my password is reset through the forgot-password loop, so that a reset I didn't request doesn't go unnoticed.
25. As a customer, I want each alert to tell me what to do if the change wasn't me, so that I can act quickly.

**Customer (brute-force protection)**

26. As a customer, I want sign-in attempts against my username to be locked out after five failures in fifteen minutes, so that a script can't guess my password.
27. As a customer, I want the lockout to apply per username and network address, so that an attacker can't lock *me* out of my own account by deliberately failing as me.
28. As a customer, I want a clear "Too many attempts — try again in 15 minutes" message when I'm locked out, so that I know why I can't sign in.
29. As a customer, I want my failed-attempt count cleared when I sign in successfully, so that an earlier typo doesn't count against me later.
30. As a customer, I want no more than three reset emails sent to my address per hour, so that nobody can use the forgot-password form to flood my inbox.

**Employee and admin**

31. As an employee, I want the same Security Center, alerts, and lockout as customers, so that the accounts with the most access are protected at least as well.
32. As the admin, I want the Django admin login to use the same failed-attempt lockout, so that the most powerful login on the site isn't the least protected.

**Demo / grading**

33. As a grader, I want the seed data to include an account with no email and accounts with a recorded password change, so that I can see every state of the Security Center without setting anything up by hand.
34. As a grader, I want to complete the reset loop using emails printed to the dev server's terminal, so that I can exercise the full flow without a mail server.

## Implementation Decisions

**User model (`accounts`)**

- The inherited `email` field becomes unique among non-blank values, ignoring case, enforced by a database-level conditional constraint. Existing accounts with blank emails remain valid; the constraint does not touch them.
- Emails are normalized on save — trimmed and lowercased — so stored values agree with the case-insensitive rule.
- A new nullable `password_changed_at` timestamp is added. Nullable for the same reason as `job_title`: unknown is not the same as empty. Null displays as "Never changed since signup."
- `User.set_password()` is overridden to stamp `password_changed_at`, but only for users that already exist (have a primary key). Django calls `set_password` on every password path — change, reset, admin, `createsuperuser` — so one override covers them all, while account creation does not count as a "change."
- One migration covers the constraint and the new field.

**Forms**

- The signup form adds a required email field. The form surfaces a friendly "an account with this email already exists" error; the database constraint remains the real guarantee.
- An email-change form takes the new email and the current password, validates the password against the signed-in user, and applies the same uniqueness check (excluding the user's own account).
- Password change reuses Django's stock password-change form, styled with DaisyUI classes like the existing forms.
- A password-reset form extends Django's stock form to apply the reset-email rate limit. Rate-limited requests are skipped silently, so the response is identical to every other request.
- A shared throttle mixin applies the login lockout. It is used by the storefront sign-in form and by a new admin sign-in form (extending Django's admin authentication form, which also enforces `is_staff`). The admin site is configured to use that form.
- All new forms carry DaisyUI widget classes, matching the existing signup and sign-in forms.

**Security module (`accounts`) — the third deliberate deep module**

- A new security service module holds the cross-cutting account-security logic, with docstrings and type hints on every public function:
  - **Login throttle:** check whether a username + IP pair may attempt sign-in, record a failure, and clear failures on success. Limit: 5 failures per 15-minute window; the lockout lasts 15 minutes.
  - **Reset-email throttle:** decide whether another reset email may be sent to an address. Limit: 3 per hour per address.
  - **Security alerts:** one function per alert (email changed, password changed, password reset completed), each rendering a plain-text email template and sending it.
- The throttle stores counters in Django's cache. The default in-memory cache works with no `.env` present.
- The project CLAUDE.md is updated in the same change from "exactly two deliberate deep modules" to three, naming this module.

**Views and URLs (`accounts` namespace)**

- **Security Center hub** — login required. Shows email or the missing-email warning, last sign-in (`last_login`), member since (`date_joined`), and password last changed.
- **Change email** — login required; on success sends the alert to the old address (only if there was one), then redirects to the hub with a success message.
- **Change password** — login required; built on Django's password-change view, which keeps the current session valid and invalidates all others. On success sends the password-changed alert and redirects to the hub with a success message.
- **Password reset request / done / confirm / complete** — built on Django's four password-reset views. The request page always shows the generic "If an account exists for that email…" result. The done page states the one-hour expiry and suggests checking spam. The confirm page handles invalid or expired links with a message and a link to request a new one. Completion sends the reset alert and redirects to the sign-in page with a success message; the user is **not** signed in automatically, matching how signup already hands off to sign-in.
- Every URL is named under the `accounts` namespace. Security Center pages live under `/accounts/security/`.
- Views stay thin: they call the security module to send alerts; throttling happens in the forms.

**Settings**

- `PASSWORD_RESET_TIMEOUT` is read from `.env` via environs, defaulting to 3600 seconds (one hour).
- `DEFAULT_FROM_EMAIL` is read from `.env`, defaulting to `ThoughtTronix <no-reply@thoughttronix.local>`.
- The email backend stays on the console backend.
- `.env.example` documents both new settings.

**Templates**

- All new pages extend the project-level base template. None are HTMX partials — these are ordinary multi-page form flows.
- Email bodies (reset email and three alerts) are plain-text templates in an `email` subfolder of the accounts templates. Each alert includes what changed, when, and a link to reset the password if the change wasn't the recipient.
- The sign-in page gains a "Forgot password?" link; the navbar user menu gains an "Account security" entry for signed-in users.

**Seed data**

- Adds one grandfathered customer with a blank email, to show the missing-email warning.
- Backdates `password_changed_at` for one or two existing demo users (for example, a staff member "changed 3 weeks ago"). Because the `set_password` override stamps "now," the backdated value is written directly after the password is set.
- All other demo users keep a null `password_changed_at`.

## Out of Scope

- **Confirming a new email by link.** Email changes take effect immediately on password confirmation; proving ownership of the new address is a future enhancement.
- **Email verification at signup.** Accounts are usable without proving the email is real. As a consequence, the signup "email already in use" error reveals that an account exists — an accepted, documented trade-off. The reset form itself never reveals it.
- **Signing in with email.** The username remains the login identifier.
- **Two-factor authentication.**
- **New sign-in alerts.** Alerts cover credential changes only; per-login emails would be noise without device recognition.
- **A security activity log** (a recorded history of sign-ins, failures, and changes, shown on the hub).
- **A "sign out of all other devices" button** independent of a password change.
- **Stricter password or lockout rules for staff.**
- **Persistent or shared throttle storage.** Counters live in the in-memory cache and reset when the server restarts; they are not shared across multiple server processes.
- **Real email delivery** (SMTP or a mail provider). The console backend is the only backend.
- **Self-service account deletion.**

## Testing Decisions

- Tests use pytest + pytest-django with plain fixtures in the project-level conftest, as for the rest of the suite. Tests never invoke the seed command.
- An autouse fixture clears the cache before each test, so throttle counts never carry from one test to the next.
- Emails are asserted through Django's test outbox: the reset email contains a working link; each alert goes to the right address (the *old* address for email changes) with the expected content; no email is sent for unknown addresses or rate-limited requests.
- The security module is tested directly, without HTTP: lockout after the fifth failure, separate counts per username + IP, clearing on success, lockout expiry, and the reset-email limit.
- Model tests cover the case-insensitive unique constraint (including that multiple blank emails are allowed), email normalization, and that `set_password` stamps `password_changed_at` for existing users but not on creation.
- View tests walk the full reset loop end to end, including expired links (by overriding the timeout), reused links, and that other sessions are invalidated after a password change or reset while the current one survives a change.
- The admin login is tested to confirm it is throttled.
- The suite stays green at the end of every phase.

## Further Notes

**How to demo the reset loop.** Run the dev server, click "Forgot password?" on the sign-in page, and submit a seeded user's email. The reset email — including the link — prints to the `runserver` terminal. Open the link, set a new password, and sign in. The "password reset" alert prints to the same terminal.

**How to demo the lockout.** Fail sign-in five times for the same username; the sixth attempt shows the lockout message even with the correct password. Restarting the dev server clears the lockout (a documented limitation of the in-memory cache).

**Why Django's built-ins.** Password change and reset are built on Django's stock views and token generator, which already provide single-use, expiring, tamper-proof links and automatic invalidation of other sessions on a password change. The feature's own code is limited to the email rules, the hub, the throttle, the alerts, and styling — the security-critical cryptography is not hand-written.

**Reset links are single-use by construction.** Django's reset token is derived from the user's current password hash and last sign-in time, so changing the password invalidates every outstanding link.
