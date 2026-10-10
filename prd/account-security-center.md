# PRD: The ThoughtTronix Store — Account Security Center

*Commissioned by ThoughtTronix Product Management. "Your Thoughts, Our Business."*

---

## Problem Statement

A ThoughtTronix customer account is a username and a password, and nothing else. Signing up never asks for an email address, so the store has no way to reach a customer about their own account.

That leaves customers stuck in three ways. A customer who forgets their password has no way back in; the account, its saved addresses, and its order history are simply lost to them. A customer who wants a new password has nowhere to change it. And because the store holds no address for them, a customer is never told when something important about their account changes — if someone else changed their password, the first sign would be that they can no longer sign in.

Customers also have to remember a username, which is the detail people forget first.

## Solution

An **Account Security Center**, plus the account email that makes it possible.

**Email on every new account.** Signing up now asks for an email address, and it is required. Each email belongs to exactly one account, and capitalization does not matter — `Erik@Example.com` and `erik@example.com` are the same address.

**The Security Center.** A signed-in page titled "Account Security", reached from a new "Account Security" link in the navbar, that shows the account's username and current email and offers two actions:

- **Change password** — enter the current password and the new one twice. The customer stays signed in on this device and is signed out everywhere else.
- **Change email** — enter the new address and the current password. Nothing changes yet: the store emails a confirmation link to the *new* address, and the change happens only when the customer opens that link and presses a confirm button. Once it does, the *old* address is told about it.

**Forgot password.** A "Forgot your password?" link on the sign-in page. The customer enters their email; the store sends a reset link that works for one hour; the customer chooses a new password and then signs in with it. The page never reveals whether an email is on file.

**Security notices.** The store emails the customer whenever their password is changed or reset, and emails the old address whenever the account's email changes.

**Sign in with username or email.** The sign-in page accepts either.

All mail is printed to the development server's console; no real mail leaves the machine.

## User Stories

**Visitor (not signed in)**

1. As a visitor, I want to give my email address when I sign up, so that I can recover my account if I forget my password.
2. As a visitor, I want sign-up to tell me when my email is already used by another account, regardless of capitalization, so that I know to sign in or reset my password instead of creating a duplicate.
3. As a visitor, I want sign-up to tell me that usernames cannot contain "@", so that my username is never mistaken for an email address at sign-in.
4. As a visitor, I want sign-up to refuse to create an account without an email, so that every new account can be recovered.

**Customer signing in**

5. As a customer, I want to sign in with either my username or my email address, so that I don't have to remember my username.
6. As a customer, I want my email to be matched regardless of capitalization at sign-in, so that typing it differently doesn't lock me out.
7. As a customer whose old username contains "@", I want to still be able to sign in with that username, so that the new email sign-in doesn't lock me out.

**Customer who forgot their password**

8. As a customer, I want a "Forgot your password?" link on the sign-in page, so that I can start recovering my account.
9. As a customer, I want to enter my email address and receive a link to reset my password, so that I can regain access without contacting staff.
10. As a customer, I want the forgot-password page to show the same message whether or not my email is on file, so that strangers cannot use it to discover who shops at ThoughtTronix.
11. As a customer, I want the reset link to stop working after one hour, so that an old email sitting in my inbox can't be used to take over my account.
12. As a customer, I want a reset link to stop working once I've used it, so that it can't be replayed.
13. As a customer, I want to choose a new password that meets the store's password rules, so that my new password is as strong as one chosen at sign-up.
14. As a customer, I want to be sent to the sign-in page with a confirmation message after resetting my password, so that I can sign in with the new password straight away.
15. As a customer, I want resetting my password to sign me out on every other device, so that anyone using my old password loses access.
16. As a customer, I want a clear message when a reset link is invalid or expired, so that I know to request a new one.

**Customer in the Security Center**

17. As a customer, I want an "Account Security" link in the navbar, so that I can find my account security settings.
18. As a customer, I want the Security Center to show my username and my current email, so that I can check what the store has on file.
19. As a customer whose account predates email at sign-up, I want the Security Center to tell me no email is on file and invite me to add one, so that I can make my account recoverable.
20. As a customer, I want to change my password by entering my current password and a new one twice, so that I can keep my account secure.
21. As a customer, I want to stay signed in on this device after changing my password, so that I'm not interrupted.
22. As a customer, I want changing my password to sign me out on every other device, so that a forgotten session elsewhere can't keep using my account.
23. As a customer, I want to be returned to the Security Center with a confirmation message after a change, so that I know it worked.
24. As a customer, I want to change my email address, so that my account stays recoverable when I change email providers or fix a typo from sign-up.
25. As a customer, I want changing my email to require my current password, so that someone using my unattended signed-in computer cannot redirect my account recovery to their own inbox.
26. As a customer, I want the change-email form to reject my current address or an address already used by another account, so that I get a clear error instead of a silent failure.
27. As a customer, I want my new email to take effect only after I confirm it from a link sent to that address, so that a typo in the new address can't quietly break my password recovery.
28. As a customer, I want to be told to check my new inbox after requesting an email change, so that I know what to do next.

**Customer confirming an email change**

29. As a customer, I want the confirmation link to open a page that shows the new address and a confirm button, so that I can review the change before it happens and so that email link-scanners can't confirm it for me.
30. As a customer, I want the confirmation page to work whether or not I'm signed in on the device where I read my email, so that I don't have to sign in on my phone first.
31. As a customer, I want the confirmation link to expire after one hour, so that a stale link can't be used later.
32. As a customer, I want a confirmation link to stop working once my email has changed, so that each link can be used only once.
33. As a customer, I want changing my password to cancel any email-change links I haven't confirmed yet, so that I can stop a change I didn't request.
34. As a customer, I want to be told if the new address was claimed by another account before I confirmed, so that I understand why the change didn't happen.
35. As a customer, I want a clear message when a confirmation link is invalid or expired, with a way back to the Security Center to request a new one, so that I'm not stuck.
36. As a customer, I want to land on the Security Center (if signed in) or the sign-in page (if not) with a message naming my new email after confirming, so that I know the change is complete.

**Security notices**

37. As a customer, I want an email to my old address when my account's email is changed, so that I find out if someone has taken over my account.
38. As a customer, I want an email when my password is changed or reset, so that I find out if someone else changed it.
39. As a customer, I want the password-reset email to name my username, so that I can also recover a forgotten username.
40. As a customer, I want every store email to come from a recognizable ThoughtTronix sender, so that I can trust it isn't phishing.

**Staff and the admin**

41. As an employee, I want to use the Security Center for my own account just as customers do, so that I can change my password or email without asking an admin.
42. As the store admin, I want superuser accounts excluded from email password reset, so that whoever controls the admin's inbox cannot take over the store; I recover my password from the command line instead.
43. As the store admin, I want the database to reject a second account with the same email (ignoring capitalization) even when I create users in the Django admin, so that the one-email-one-account rule holds everywhere.
44. As the store admin, I want to create staff accounts in the Django admin without an email, so that the new requirement doesn't block accounts created outside sign-up.

## Implementation Decisions

**Models and database**

- `accounts.User` keeps the `email` field it inherits from `AbstractUser`, changed to be nullable. A missing email is stored as NULL, never an empty string, so accounts without one do not collide with each other.
- Uniqueness is enforced in the database by a unique constraint on the lowercased email, making it case-insensitive. The email itself is stored exactly as the customer typed it. Nullable text fields trip ruff's DJ001 rule; it is silenced on this field with a comment explaining why, as `job_title` already is.
- The migration includes a data step that converts existing empty-string emails to NULL *before* adding the constraint, so accounts created through the old email-less sign-up do not make the migration fail.
- No other model or field is added. In particular, no "pending email" or "email verified" state is stored — see the email-change token below.

**Sign-up form**

- The sign-up form adds a required email field. It validates the email with a case-insensitive lookup and shows a friendly field error when the address is taken; the database constraint is the backstop.
- The sign-up form rejects usernames containing "@".
- Requiring an email is a form rule, not a database rule: accounts created outside sign-up (the Django admin, `createsuperuser`, the shell, the seed command) may still have no email.

**Sign-in**

- A custom authentication backend, registered in the authentication backends setting, lets customers sign in with a username or an email. Input containing "@" is matched first as an email (case-insensitive), then as a username, so legacy usernames containing "@" still work. Other input is matched as a username.
- The backend keeps Django's standard checks: an inactive user cannot sign in, and the backend runs the password hasher even when no user matches, so response timing does not reveal which accounts exist.
- The sign-in field is relabeled "Username or email".

**Security Center (signed in, everyone)**

- A hub page in the accounts app, named and namespaced like the rest of accounts (for example, `accounts:security`), behind a login requirement. It shows the username and the current email, or a "No email on file — add one" prompt, and links to the two action pages. This mirrors the address book's shape: a list page plus separate form pages that redirect back with a flash message.
- **Change password** is Django's built-in password-change view, styled in DaisyUI, redirecting to the hub with a success message. Django already keeps the current session signed in and invalidates all other sessions.
- **Change email** is a form view taking the new email and the current password. The form validates the current password, rejects the account's current email (case-insensitive), and rejects an email already used by another account. On success it emails a confirmation link to the new address and redirects to the hub with a "Check new@… for a confirmation link" message. The account's email is not changed at this step.
- The Security Center is available to every signed-in user — customers, employees, and the superuser. No role checks.
- The hub's page heading is "Account Security", and an "Account Security" link joins the signed-in navbar beside "Addresses".

**Email-change confirmation token**

- The confirmation link carries a stateless signed token built with Django's signing framework, using a dedicated salt. Its payload holds the user's id, the new email, the email current at request time, and a fingerprint of the account's password hash.
- The token is valid for one hour. It is rejected if it has expired, has been tampered with, the account's current email no longer matches the one in the token (so each link works once), or the password fingerprint no longer matches (so a password change cancels pending links).
- Because nothing is stored, the hub cannot show a pending change and a customer cannot cancel a request except by changing their password or letting it expire. This trade-off was accepted.

**Email-change confirm view**

- Opening the link (GET) never changes anything. It shows the new address and a "Confirm new email" button; the change is applied only by submitting that form (POST, CSRF-protected). This keeps email link-scanners from confirming changes.
- The view does not require sign-in; the token alone identifies and authorizes the change.
- On submit, uniqueness is checked again. If another account claimed the address in the meantime, the page shows "That email is now in use by another account" and changes nothing.
- An invalid, expired, used, or cancelled token shows a single "This link is invalid or has expired" message, with a link to the Security Center.
- On success the email is saved, the old address (if there was one) is sent a notice, and the customer is redirected to the hub if signed in or to the sign-in page if not, with a message naming the new email.

**Forgot password**

- Uses Django's four built-in password-reset views (request, "check your email", set new password, done), styled in DaisyUI and placed in the accounts namespace. A "Forgot your password?" link is added to the sign-in page.
- The request page always shows the same message — "If an account exists for that email, we've sent a link to reset your password" — whether or not the email matches an account. This is Django's default behavior.
- The reset form is customized to skip superusers. Django already skips inactive users and users with unusable passwords (such as the seeded background customers).
- The reset email template is overridden to brand it and to name the account's username.
- The reset link lifetime is set to one hour with a plain constant in settings, with a comment explaining why; it is not read from `.env`.
- After setting a new password the customer is not signed in automatically. They are sent to the sign-in page with a success message. Changing the password invalidates all existing sessions.

**Security notices**

- "Your password was changed" goes to the account's email after a password change from the Security Center and after a password reset. Accounts without an email are skipped.
- "Your email was changed to n\*\*\*@…" goes to the *old* address when an email change is confirmed. There is no notice when a change is requested. An account with no previous email is skipped.
- Each notice is a plain-text email template rendered and sent from the view that completes the action. No service module is needed: none of these is a cross-model workflow.

**Mail configuration**

- The email backend stays the console backend; all mail prints to the development server's terminal.
- `DEFAULT_FROM_EMAIL` is set to `ThoughtTronix <no-reply@thoughttronix.example>`.

**Seed command**

- Seeded users already have unique emails derived from their usernames, so the demo world satisfies the new constraint without changes.

## Out of Scope

- **Rate limiting and lockout** on sign-in, forgot-password, and change-email.
- **Verifying the sign-up email.** The email given at sign-up is saved immediately; only *changes* are confirmed by link. There is no "email verified" account state.
- **Showing or cancelling a pending email change** in the Security Center, beyond changing the password to cancel it.
- **A notice to the old address when a change is requested** (only when one is confirmed).
- **Real email delivery** (SMTP or any provider). Mail stays on the console backend.
- **Two-factor authentication.**
- **Session management**: listing or revoking active sessions or devices.
- **Email password reset for superusers.** They use `manage.py changepassword`.
- **Auto-login** after sign-up or after a password reset.
- **Changing the username.**

## Further Notes

- **Testing** follows the project convention: pytest with pytest-django, plain fixtures in the shared conftest, and a green suite at every phase boundary. Email behavior is tested through Django's in-memory outbox. Coverage should include:
  - the case-insensitive uniqueness rule, at both the form and the database;
  - the empty-string-to-NULL migration step;
  - the "@"-in-username guard, and the backend's lookup order, including a legacy "@" username and a superuser signing in;
  - each token rejection reason (expired, tampered, email already changed, password changed);
  - the re-check of uniqueness when a change is confirmed;
  - that opening the confirmation link alone changes nothing;
  - that superusers receive no reset email while the page still shows the same message;
  - each notice going to the right address, and being skipped when no address is on file.
- The core platform's sign-up deliberately asked for no email ("signing up asks for the minimum"). This PRD reverses that choice, and the sign-up form's docstring should say so.
- The core platform's settings note that "real mail is out of scope for the core." That remains true; this feature is designed to be demonstrated through the console, where reset and confirmation links can be copied into the browser.
- Old accounts with no email can still sign in by username and add an email through the confirmed change flow, so nobody is locked out by the migration.
