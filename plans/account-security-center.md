# Plan: The ThoughtTronix Store — Account Security Center

> Source PRD: `prd/account-security-center.md`. The PRD owns the requirements; this plan owns the sequence. Where the two seem to disagree, the PRD's wording is authoritative.

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: `accounts`, mounted at `/accounts/` under the `accounts:` namespace. No new app.
- **URLs**:
  - `/accounts/security/`: `accounts:security`, the Security Center hub
  - `/accounts/security/password/`: `accounts:password_change`
  - `/accounts/security/email/`: `accounts:email_change`
  - `/accounts/security/email/confirm/<token>/`: `accounts:email_confirm`
  - `/accounts/password-reset/`: `accounts:password_reset` (request)
  - `/accounts/password-reset/sent/`: `accounts:password_reset_done`
  - `/accounts/password-reset/<uidb64>/<token>/`: `accounts:password_reset_confirm`
  - `/accounts/password-reset/complete/`: `accounts:password_reset_complete`
- **Models**: `accounts.User.email` (inherited from `AbstractUser`) becomes nullable. A missing email is NULL, never `""`, and the DJ001 rule is silenced with a comment, as on `job_title`. The database enforces a unique constraint on the lowercased email. The email itself is stored as typed. The migration converts `""` to NULL before adding the constraint. No other model or field is added, and there is no pending-email or verified-email state.
- **Authentication**: a custom email-or-username backend, registered in `AUTHENTICATION_BACKENDS`. Input containing "@" is tried as a case-insensitive email first, then as a username. Any other input is matched as a username. The backend keeps Django's inactive-user check and its timing-safe hasher run.
- **Authorization**: the Security Center and its action pages need sign-in only, with no role checks. Customers, employees and the superuser all use it. The email-confirm view needs no sign-in; its signed token alone authorizes the change.
- **Email-change token**: stateless, built with Django's signing framework under a dedicated salt. The payload holds the user id, the new email, the email current at request time, and a fingerprint of the password hash. It is valid for one hour.
- **Mail**: stays on the console backend. `DEFAULT_FROM_EMAIL = "ThoughtTronix <no-reply@thoughttronix.example>"`. Each notice is a plain-text template rendered and sent from the view that completes the action. There is no service module.
- **Password-reset lifetime**: one hour, set as a plain constant in settings with an explanatory comment. It is not read from `.env`.

---

## Phase 1: An email on every new account

**User stories**: 1, 2, 3, 4, 43, 44

### What to build

Make the account email a real, unique field and ask for it at sign-up. `User.email` becomes nullable, with the case-insensitive unique constraint. The migration's data step turns existing empty-string emails into NULL first, so email-less accounts from the old sign-up migrate cleanly. The sign-up form gains a required email field and shows a friendly field error when the address is taken in any capitalization. It also rejects usernames containing "@". The form's docstring records that this reverses the core platform's "signing up asks for the minimum" choice. Requiring an email is a form rule only. The Django admin, `createsuperuser`, the shell and `seed` can still create accounts without one.

### Acceptance criteria

- [ ] Sign-up without an email is refused with a field error
- [ ] Sign-up with an email already on file in different capitalization (`Erik@Example.com` vs `erik@example.com`) shows a friendly field error and creates no account
- [ ] Sign-up with "@" in the username is refused with a field error that explains why
- [ ] A successful sign-up stores the email exactly as typed
- [ ] Saving a second user whose email differs only in case raises an integrity error at the database, outside the form
- [ ] Several users with no email (NULL) can coexist
- [ ] The migration's data step converts existing `""` emails to NULL. A test covers it.
- [ ] A user can still be created with no email outside sign-up (e.g. `create_user` without an email)
- [ ] `seed` still runs cleanly against the new constraint
- [ ] Test suite green, ruff clean

---

## Phase 2: Sign in with username or email, and the Security Center hub

**User stories**: 5, 6, 7, 17, 18, 19, 41 (hub)

### What to build

Two things land in this phase.

**Sign-in.** Add the custom authentication backend, register it in settings, and relabel the sign-in field "Username or email". A customer can sign in with either. An email matches regardless of capitalization. A legacy username that contains "@" still works because of the email-then-username lookup order. Inactive users are still refused. When no user matches, the password hasher still runs.

**The hub.** Build the signed-in Security Center at `accounts:security`, headed "Account Security" and reached from a new "Account Security" link beside "Addresses" in the navbar. It shows the username and current email. When no email is on file, it shows a "No email on file — add one" prompt instead. It follows the address book's shape: a list-style page that later phases' form pages redirect back to with a flash message. Its action links are added by the phases that build those actions.

### Acceptance criteria

- [ ] Sign-in succeeds with the username
- [ ] Sign-in succeeds with the email in any capitalization
- [ ] A legacy user whose username contains "@" (and matches no email) can sign in with that username
- [ ] A superuser can sign in through the store's sign-in page
- [ ] An inactive user cannot sign in by username or by email
- [ ] A wrong password fails for both username and email input
- [ ] The sign-in field is labeled "Username or email"
- [ ] An anonymous visitor to the hub is redirected to sign-in
- [ ] The hub shows the signed-in user's username and email
- [ ] For a user with no email, the hub shows the "No email on file" prompt
- [ ] A customer, an employee and the superuser can each open the hub
- [ ] The navbar shows "Account Security" for signed-in users only
- [ ] Test suite green, ruff clean

---

## Phase 3: Change password

**User stories**: 20, 21, 22, 23, 38 (password changed), 40, 41 (change password)

### What to build

Add the hub's first action, change password, using Django's built-in password-change view styled in DaisyUI and linked from the hub. It redirects to the hub with a success message, keeps this session signed in, and ends the account's other sessions. It sends a "Your password was changed" notice to the account's email, and skips the notice when no email is on file. This is the store's first outgoing email, so this phase also sets `DEFAULT_FROM_EMAIL` to give every store email the ThoughtTronix sender.

### Acceptance criteria

- [ ] An anonymous visitor to the change-password page is redirected to sign-in
- [ ] The hub links to the change-password page
- [ ] A customer, an employee and the superuser can each change their password
- [ ] Changing the password requires the current password and the new one twice, and enforces the store's password validators
- [ ] After a change the user is still signed in on this session, lands on the hub, and sees a confirmation message
- [ ] Another session for the same user is no longer authenticated after the change
- [ ] A "password changed" notice goes to the account's email from the ThoughtTronix sender. No mail is sent when the account has no email.
- [ ] Test suite green, ruff clean

---

## Phase 4: Forgot password

**User stories**: 8, 9, 10, 11, 12, 13, 14, 15, 16, 38 (password reset), 39, 42

### What to build

Wire Django's four built-in password-reset views into the accounts namespace and style them in DaisyUI. Add a "Forgot your password?" link to the sign-in page. The request page always shows "If an account exists for that email, we've sent a link to reset your password", whether or not the email matches. The reset form is customized to skip superusers, on top of Django's own skipping of inactive users and unusable passwords. Override the reset email to carry ThoughtTronix branding and name the account's username. Set the link lifetime to one hour. After choosing a new password, the customer is not signed in. They land on the sign-in page with a success message, all their existing sessions are ended, and a "password changed" notice is sent.

### Acceptance criteria

- [ ] The sign-in page links to the forgot-password page
- [ ] Requesting a reset for a known customer email sends one email containing a working reset link and the account's username
- [ ] Requesting a reset for an unknown email sends nothing and shows the same message as a known one
- [ ] Requesting a reset for a superuser's email sends nothing and shows the same message
- [ ] Email matching on the request page ignores capitalization
- [ ] The new password must pass the store's password validators
- [ ] After a reset, the user lands on the sign-in page with a success message and is not signed in, and they can sign in with the new password
- [ ] A used reset link and a link older than one hour each show a clear invalid-or-expired message
- [ ] Existing sessions for the user are no longer authenticated after a reset
- [ ] A "password changed" notice is sent after a reset
- [ ] Test suite green, ruff clean

---

## Phase 5: Change email, confirmed by link

**User stories**: 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37

### What to build

Complete the hub's second action from end to end.

**Request.** At `accounts:email_change`, linked from the hub (including from its "No email on file" prompt), a signed-in user enters a new email and their current password. The form checks the password and rejects the account's current email (case-insensitive) and any email used by another account. On success, nothing about the account changes yet. A confirmation email carrying the signed token link goes to the *new* address, and the user returns to the hub with a "Check new@… for a confirmation link" message.

**Confirm.** Opening `accounts:email_confirm` works with or without being signed in. A GET never changes anything: it shows the new address and a "Confirm new email" button. Only the CSRF-protected POST applies the change, which keeps email link-scanners from confirming it. Every invalid token (expired, tampered, email already changed since the request, password changed since the request) gets one "This link is invalid or has expired" message, with a link to the Security Center. On POST, uniqueness is checked again. If another account claimed the address in the meantime, the page says "That email is now in use by another account" and changes nothing. On success the email is saved and the *old* address, if there was one, is sent a "Your email was changed to n\*\*\*@…" notice. The user is redirected to the hub if signed in, or to sign-in if not, with a message naming the new email.

### Acceptance criteria

- [ ] An anonymous visitor to the change-email page is redirected to sign-in
- [ ] The hub, including its "No email on file" prompt, links to the change-email page
- [ ] A wrong current password is rejected with a field error
- [ ] The account's current email, in any capitalization, is rejected
- [ ] An email used by another account, in any capitalization, is rejected
- [ ] A valid request sends one confirmation email to the new address, leaves the account's email unchanged, and redirects to the hub with the "check your inbox" message
- [ ] A user with no email can request and confirm an email, and no old-address notice is sent
- [ ] A GET on a valid confirmation link shows the new address and a confirm button, and changes nothing
- [ ] Each rejection reason (expired after one hour, tampered, email already changed, password changed since the request) shows the invalid-or-expired page with a link back to the Security Center. Each reason has its own test.
- [ ] A link cannot be used twice: after a successful confirm, the same link is rejected
- [ ] If another account claims the address before confirmation, the POST shows the "now in use" message and changes nothing
- [ ] A successful confirm while signed in redirects to the hub with a message naming the new email
- [ ] A successful confirm while signed out redirects to sign-in with that message
- [ ] The old address receives the masked "email was changed" notice. No notice is sent when a change is only requested.
- [ ] After the change, the user can sign in with the new email, and the old email no longer signs them in
- [ ] Test suite green, ruff clean
