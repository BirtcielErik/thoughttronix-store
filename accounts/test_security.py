"""Sign-in by username or email, the Security Center hub, its actions, and
forgot password."""

import re
import time
from datetime import datetime, timedelta
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import get_hasher
from django.contrib.auth.tokens import default_token_generator
from django.contrib.messages import get_messages
from django.core import mail
from django.test import Client
from django.urls import reverse


@pytest.fixture
def erik(db):
    return get_user_model().objects.create_user(
        username="erik", email="Erik@Example.com", password="erik-pass-123"
    )


def sign_in(client, username, password):
    return client.post(
        reverse("accounts:login"), {"username": username, "password": password}
    )


def signed_in_user(client):
    return client.get(reverse("products:catalog")).context["user"]


# --- Sign-in -----------------------------------------------------------------


def test_sign_in_with_username(client, erik):
    sign_in(client, "erik", "erik-pass-123")

    assert signed_in_user(client) == erik


@pytest.mark.parametrize(
    "email", ["Erik@Example.com", "erik@example.com", "ERIK@EXAMPLE.COM"]
)
def test_sign_in_with_email_in_any_capitalization(client, erik, email):
    sign_in(client, email, "erik-pass-123")

    assert signed_in_user(client) == erik


def test_legacy_username_with_at_sign_still_signs_in(client, db):
    legacy = get_user_model().objects.create_user(
        username="old@timer", password="legacy-pass-123"
    )

    sign_in(client, "old@timer", "legacy-pass-123")

    assert signed_in_user(client) == legacy


def test_superuser_signs_in_through_the_store(client, superuser):
    sign_in(client, "admin", "admin123")

    assert signed_in_user(client) == superuser


@pytest.mark.parametrize("login", ["erik", "erik@example.com"])
def test_inactive_user_cannot_sign_in(client, erik, login):
    erik.is_active = False
    erik.save()

    response = sign_in(client, login, "erik-pass-123")

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].non_field_errors()
    assert not signed_in_user(client).is_authenticated


@pytest.mark.parametrize("login", ["erik", "erik@example.com"])
def test_wrong_password_fails(client, erik, login):
    response = sign_in(client, login, "not-the-password")

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].non_field_errors()
    assert not signed_in_user(client).is_authenticated


@pytest.mark.parametrize("login", ["nobody", "nobody@example.com"])
def test_unknown_login_still_runs_the_hasher(client, db, monkeypatch, login):
    hasher_class = type(get_hasher())
    calls = []
    original = hasher_class.encode

    def counting_encode(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(hasher_class, "encode", counting_encode)

    response = sign_in(client, login, "whatever-123")

    assert response.context["form"].non_field_errors()
    assert calls, "no hash computed — timing would reveal the missing account"


def test_sign_in_field_is_labeled_username_or_email(client, db):
    response = client.get(reverse("accounts:login"))

    assert response.context["form"].fields["username"].label == "Username or email"
    assert "Username or email" in response.content.decode()


# --- The hub -----------------------------------------------------------------


def test_hub_redirects_visitors_to_sign_in(client, db):
    url = reverse("accounts:security")

    response = client.get(url)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"


def test_hub_shows_username_and_email(client, erik):
    client.force_login(erik)

    page = client.get(reverse("accounts:security")).content.decode()

    assert "<h1" in page and "Account Security</h1>" in page
    assert "erik" in page
    assert "Erik@Example.com" in page
    assert "No email on file" not in page


def test_hub_prompts_for_an_email_when_none_is_on_file(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert "No email on file" in page


@pytest.mark.parametrize("who", ["customer", "staff_user", "superuser"])
def test_everyone_signed_in_can_open_the_hub(client, request, who):
    user = request.getfixturevalue(who)
    client.force_login(user)

    response = client.get(reverse("accounts:security"))

    assert response.status_code == HTTPStatus.OK
    assert user.username in response.content.decode()


def test_navbar_shows_security_to_signed_in_users_only(client, customer):
    link = f'href="{reverse("accounts:security")}"'
    assert link not in client.get(reverse("products:catalog")).content.decode()

    client.force_login(customer)

    page = client.get(reverse("products:catalog")).content.decode()
    assert link in page
    assert "Account Security" in page


# --- Change password ---------------------------------------------------------

NEW_PASSWORD = "fresh-Thoughts-2026"


def change_password(client, old, new1=NEW_PASSWORD, new2=None, **kwargs):
    return client.post(
        reverse("accounts:password_change"),
        {
            "old_password": old,
            "new_password1": new1,
            "new_password2": new1 if new2 is None else new2,
        },
        **kwargs,
    )


def test_change_password_redirects_visitors_to_sign_in(client, db):
    url = reverse("accounts:password_change")

    response = client.get(url)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"


def test_hub_links_to_change_password(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert f'href="{reverse("accounts:password_change")}"' in page


@pytest.mark.parametrize(
    ("who", "password"),
    [
        ("customer", "customer123"),
        ("staff_user", "employee123"),
        ("superuser", "admin123"),
    ],
)
def test_everyone_signed_in_can_change_their_password(client, request, who, password):
    user = request.getfixturevalue(who)
    client.force_login(user)

    response = change_password(client, password)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("accounts:security")
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)


def test_wrong_current_password_is_rejected(client, customer):
    client.force_login(customer)

    response = change_password(client, "not-the-password")

    assert response.context["form"].errors["old_password"]
    customer.refresh_from_db()
    assert customer.check_password("customer123")


def test_new_passwords_must_match(client, customer):
    client.force_login(customer)

    response = change_password(client, "customer123", new2="something-Else-2026")

    assert response.context["form"].errors["new_password2"]
    customer.refresh_from_db()
    assert customer.check_password("customer123")


@pytest.mark.parametrize("weak", ["short1", "password123", "8675309112"])
def test_new_password_must_pass_the_store_validators(client, customer, weak):
    client.force_login(customer)

    response = change_password(client, "customer123", new1=weak)

    assert response.context["form"].errors["new_password2"]
    customer.refresh_from_db()
    assert customer.check_password("customer123")


def test_change_keeps_this_session_and_confirms_on_the_hub(client, customer):
    client.force_login(customer)

    response = change_password(client, "customer123", follow=True)

    assert response.redirect_chain[-1][0] == reverse("accounts:security")
    assert response.context["user"] == customer
    assert [str(m) for m in get_messages(response.wsgi_request)] == [
        "Password changed. You've been signed out everywhere else."
    ]
    assert 'class="alert alert-success"' in response.content.decode()


def test_change_signs_out_other_sessions(client, customer):
    elsewhere = Client()
    elsewhere.force_login(customer)
    assert signed_in_user(elsewhere) == customer
    client.force_login(customer)

    change_password(client, "customer123")

    assert not signed_in_user(elsewhere).is_authenticated
    assert signed_in_user(client) == customer


def test_change_sends_a_notice_from_thoughttronix(client, erik):
    client.force_login(erik)

    change_password(client, "erik-pass-123")

    assert len(mail.outbox) == 1
    notice = mail.outbox[0]
    assert notice.to == ["Erik@Example.com"]
    assert notice.from_email == "ThoughtTronix <no-reply@thoughttronix.example>"
    assert "password" in notice.subject.lower()
    assert "erik" in notice.body
    # Plain-text mail convention; longer lines are sent quoted-printable.
    assert all(len(line) <= 78 for line in notice.body.splitlines())


def test_no_notice_when_no_email_is_on_file(client, customer):
    client.force_login(customer)

    change_password(client, "customer123")

    assert mail.outbox == []


# --- Forgot password ---------------------------------------------------------

SAME_MESSAGE = "If an account exists for that email, we've sent a link"
INVALID_LINK = "This link is invalid or has expired."


def request_reset(client, email):
    return client.post(
        reverse("accounts:password_reset"), {"email": email}, follow=True
    )


def reset_link(message):
    return re.search(r"http://testserver(/\S+)", message.body).group(1)


def set_new_password(client, link, new1=NEW_PASSWORD, new2=None):
    """Open the emailed link, then post the new password to where it leads.

    Django swaps the token out of the URL for "set-password" before
    showing the form, so the POST goes to the redirect target.
    """
    opened = client.get(link)
    assert opened.status_code == HTTPStatus.FOUND
    return client.post(
        opened.url,
        {"new_password1": new1, "new_password2": new1 if new2 is None else new2},
        follow=True,
    )


def test_sign_in_page_links_to_forgot_password(client, db):
    page = client.get(reverse("accounts:login")).content.decode()

    assert f'href="{reverse("accounts:password_reset")}"' in page
    assert "Forgot your password?" in page


def test_reset_request_sends_a_link_naming_the_username(client, erik):
    response = request_reset(client, "Erik@Example.com")

    assert response.redirect_chain[-1][0] == reverse("accounts:password_reset_done")
    assert SAME_MESSAGE in response.content.decode()
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["Erik@Example.com"]
    assert message.from_email == "ThoughtTronix <no-reply@thoughttronix.example>"
    assert "ThoughtTronix" in message.subject
    assert "your username is: erik" in message.body
    assert client.get(reset_link(message)).status_code == HTTPStatus.FOUND


def test_reset_request_ignores_capitalization(client, erik):
    request_reset(client, "ERIK@example.COM")

    assert [m.to for m in mail.outbox] == [["Erik@Example.com"]]


@pytest.mark.parametrize(
    "email", ["nobody@example.com", "admin@example.com"], ids=["unknown", "superuser"]
)
def test_reset_request_sends_nothing_but_says_the_same(client, superuser, email):
    response = request_reset(client, email)

    assert response.redirect_chain[-1][0] == reverse("accounts:password_reset_done")
    assert SAME_MESSAGE in response.content.decode()
    assert mail.outbox == []


def test_reset_lands_on_sign_in_signed_out_with_a_message(client, erik):
    request_reset(client, "erik@example.com")

    response = set_new_password(client, reset_link(mail.outbox[0]))

    assert response.redirect_chain[-1][0] == reverse("accounts:login")
    assert not response.context["user"].is_authenticated
    assert [str(m) for m in get_messages(response.wsgi_request)] == [
        "Your password has been reset. Sign in with your new password."
    ]
    assert 'class="alert alert-success"' in response.content.decode()
    sign_in(client, "erik", NEW_PASSWORD)
    assert signed_in_user(client) == erik


@pytest.mark.parametrize("weak", ["short1", "password123", "8675309112"])
def test_reset_password_must_pass_the_store_validators(client, erik, weak):
    request_reset(client, "erik@example.com")

    response = set_new_password(client, reset_link(mail.outbox[0]), new1=weak)

    assert response.context["form"].errors["new_password2"]
    erik.refresh_from_db()
    assert erik.check_password("erik-pass-123")


def test_reset_passwords_must_match(client, erik):
    request_reset(client, "erik@example.com")

    response = set_new_password(
        client, reset_link(mail.outbox[0]), new2="something-Else-2026"
    )

    assert response.context["form"].errors["new_password2"]
    erik.refresh_from_db()
    assert erik.check_password("erik-pass-123")


def test_used_reset_link_is_invalid(client, erik):
    request_reset(client, "erik@example.com")
    link = reset_link(mail.outbox[0])
    set_new_password(client, link)

    response = client.get(link)

    assert response.status_code == HTTPStatus.OK
    assert INVALID_LINK in response.content.decode()
    assert response.context["form"] is None


@pytest.mark.parametrize(
    ("age", "valid"),
    [(timedelta(minutes=59), True), (timedelta(hours=1, minutes=1), False)],
)
def test_reset_link_lasts_one_hour(client, erik, monkeypatch, age, valid):
    request_reset(client, "erik@example.com")
    link = reset_link(mail.outbox[0])
    later = datetime.now() + age
    monkeypatch.setattr(default_token_generator, "_now", lambda: later)

    response = client.get(link)

    if valid:
        assert response.status_code == HTTPStatus.FOUND
    else:
        assert INVALID_LINK in response.content.decode()


def test_tampered_reset_link_is_invalid(client, erik):
    request_reset(client, "erik@example.com")

    response = client.get(reset_link(mail.outbox[0])[:-3] + "xx/")

    assert INVALID_LINK in response.content.decode()


def test_reset_signs_out_existing_sessions(client, erik):
    elsewhere = Client()
    elsewhere.force_login(erik)
    assert signed_in_user(elsewhere) == erik

    request_reset(client, "erik@example.com")
    set_new_password(client, reset_link(mail.outbox[0]))

    assert not signed_in_user(elsewhere).is_authenticated


def test_reset_sends_a_password_changed_notice(client, erik):
    request_reset(client, "erik@example.com")

    set_new_password(client, reset_link(mail.outbox[0]))

    assert len(mail.outbox) == 2
    notice = mail.outbox[1]
    assert notice.to == ["Erik@Example.com"]
    assert notice.subject == "Your ThoughtTronix password was changed"


def test_complete_page_alone_redirects_to_sign_in_without_a_message(client, db):
    response = client.get(reverse("accounts:password_reset_complete"), follow=True)

    assert response.redirect_chain[-1][0] == reverse("accounts:login")
    assert list(get_messages(response.wsgi_request)) == []


# --- Change email ------------------------------------------------------------

NEW_EMAIL = "Erik.New@Example.org"


def request_email_change(client, email=NEW_EMAIL, password="erik-pass-123"):
    return client.post(
        reverse("accounts:email_change"),
        {"email": email, "password": password},
        follow=True,
    )


def confirm_link(message):
    return re.search(r"http://testserver(/\S+)", message.body).group(1)


def test_change_email_redirects_visitors_to_sign_in(client, db):
    url = reverse("accounts:email_change")

    response = client.get(url)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"


@pytest.mark.parametrize("who", ["erik", "customer"], ids=["email", "no-email"])
def test_hub_links_to_change_email(client, request, who):
    user = request.getfixturevalue(who)
    client.force_login(user)

    page = client.get(reverse("accounts:security")).content.decode()

    assert f'href="{reverse("accounts:email_change")}"' in page


def test_no_email_prompt_links_to_change_email(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    prompt = page[page.index("No email on file") :]
    assert f'href="{reverse("accounts:email_change")}"' in prompt.split("</div>")[0]


def test_change_email_rejects_a_wrong_password(client, erik):
    client.force_login(erik)

    response = request_email_change(client, password="not-the-password")

    assert response.context["form"].errors["password"]
    assert mail.outbox == []


@pytest.mark.parametrize("email", ["Erik@Example.com", "erik@EXAMPLE.com"])
def test_change_email_rejects_the_current_email(client, erik, email):
    client.force_login(erik)

    response = request_email_change(client, email=email)

    assert response.context["form"].errors["email"] == ["That is already your email."]
    assert mail.outbox == []


@pytest.mark.parametrize("email", ["admin@example.com", "ADMIN@Example.COM"])
def test_change_email_rejects_another_accounts_email(client, erik, superuser, email):
    client.force_login(erik)

    response = request_email_change(client, email=email)

    assert response.context["form"].errors["email"] == [
        "That email is in use by another account."
    ]
    assert mail.outbox == []


def test_change_request_emails_the_new_address_only(client, erik):
    client.force_login(erik)

    response = request_email_change(client)

    assert response.redirect_chain[-1][0] == reverse("accounts:security")
    assert [str(m) for m in get_messages(response.wsgi_request)] == [
        f"Check {NEW_EMAIL} for a confirmation link."
    ]
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [NEW_EMAIL]
    assert message.from_email == "ThoughtTronix <no-reply@thoughttronix.example>"
    assert "erik" in message.body
    assert confirm_link(message).startswith("/accounts/security/email/confirm/")
    erik.refresh_from_db()
    assert erik.email == "Erik@Example.com"


def test_opening_the_link_shows_the_change_and_changes_nothing(client, erik):
    client.force_login(erik)
    request_email_change(client)

    response = client.get(confirm_link(mail.outbox[0]))

    page = response.content.decode()
    assert response.status_code == HTTPStatus.OK
    assert NEW_EMAIL in page
    assert 'method="post"' in page
    assert "Confirm new email</button>" in page
    erik.refresh_from_db()
    assert erik.email == "Erik@Example.com"
    assert len(mail.outbox) == 1


def test_confirm_while_signed_in_lands_on_the_hub(client, erik):
    client.force_login(erik)
    request_email_change(client)

    response = client.post(confirm_link(mail.outbox[0]), follow=True)

    assert response.redirect_chain[-1][0] == reverse("accounts:security")
    assert [str(m) for m in get_messages(response.wsgi_request)] == [
        f"Your email is now {NEW_EMAIL}."
    ]
    erik.refresh_from_db()
    assert erik.email == NEW_EMAIL


def test_confirm_while_signed_out_lands_on_sign_in(client, erik):
    client.force_login(erik)
    request_email_change(client)
    link = confirm_link(mail.outbox[0])
    phone = Client()

    response = phone.post(link, follow=True)

    assert response.redirect_chain[-1][0] == reverse("accounts:login")
    assert [str(m) for m in get_messages(response.wsgi_request)] == [
        f"Your email is now {NEW_EMAIL}."
    ]
    erik.refresh_from_db()
    assert erik.email == NEW_EMAIL


def test_confirm_sends_the_old_address_a_masked_notice(client, erik):
    client.force_login(erik)
    request_email_change(client)

    client.post(confirm_link(mail.outbox[0]))

    assert len(mail.outbox) == 2
    notice = mail.outbox[1]
    assert notice.to == ["Erik@Example.com"]
    assert notice.from_email == "ThoughtTronix <no-reply@thoughttronix.example>"
    assert "E***@Example.org" in notice.body
    assert NEW_EMAIL not in notice.body
    assert all(len(line) <= 78 for line in notice.body.splitlines())


def test_user_with_no_email_can_add_one_without_a_notice(client, customer):
    client.force_login(customer)
    request_email_change(client, email="customer@example.com", password="customer123")

    client.post(confirm_link(mail.outbox[0]))

    customer.refresh_from_db()
    assert customer.email == "customer@example.com"
    assert len(mail.outbox) == 1


def test_link_works_once(client, erik):
    client.force_login(erik)
    request_email_change(client)
    link = confirm_link(mail.outbox[0])
    client.post(link)

    response = client.get(link)

    assert INVALID_LINK in response.content.decode()


def assert_invalid_link_page(response):
    page = response.content.decode()
    assert response.status_code == HTTPStatus.OK
    assert INVALID_LINK in page
    assert f'href="{reverse("accounts:security")}"' in page
    assert "Confirm new email</button>" not in page


@pytest.mark.parametrize(
    ("age", "valid"),
    [(timedelta(minutes=59), True), (timedelta(hours=1, minutes=1), False)],
)
def test_confirm_link_lasts_one_hour(client, erik, monkeypatch, age, valid):
    issued = time.time() - age.total_seconds()
    with monkeypatch.context() as m:
        m.setattr(time, "time", lambda: issued)
        token = erik.make_email_change_token(NEW_EMAIL)
    link = reverse("accounts:email_confirm", kwargs={"token": token})

    response = client.post(link)

    erik.refresh_from_db()
    if valid:
        assert response.status_code == HTTPStatus.FOUND
        assert erik.email == NEW_EMAIL
    else:
        assert_invalid_link_page(response)
        assert erik.email == "Erik@Example.com"


def test_tampered_confirm_link_is_invalid(client, erik):
    _, signature = erik.make_email_change_token(NEW_EMAIL).split(":", 1)
    # A payload naming another address, under the original's signature.
    payload, _ = erik.make_email_change_token("thief@example.com").split(":", 1)
    forged = f"{payload}:{signature}"

    response = client.post(reverse("accounts:email_confirm", kwargs={"token": forged}))

    assert_invalid_link_page(response)
    erik.refresh_from_db()
    assert erik.email == "Erik@Example.com"


def test_confirm_link_dies_when_the_email_changed_since(client, erik):
    token = erik.make_email_change_token(NEW_EMAIL)
    erik.email = "elsewhere@example.com"
    erik.save()

    response = client.post(reverse("accounts:email_confirm", kwargs={"token": token}))

    assert_invalid_link_page(response)
    erik.refresh_from_db()
    assert erik.email == "elsewhere@example.com"


def test_changing_the_password_cancels_pending_links(client, erik):
    client.force_login(erik)
    request_email_change(client)
    link = confirm_link(mail.outbox[0])
    change_password(client, "erik-pass-123")

    response = client.post(link)

    assert_invalid_link_page(response)
    erik.refresh_from_db()
    assert erik.email == "Erik@Example.com"


def test_address_claimed_before_confirming_changes_nothing(client, erik):
    client.force_login(erik)
    request_email_change(client)
    get_user_model().objects.create_user(
        username="quick", email=NEW_EMAIL.upper(), password="quick-pass-123"
    )

    response = client.post(confirm_link(mail.outbox[0]))

    assert response.status_code == HTTPStatus.OK
    assert "That email is now in use by another account." in response.content.decode()
    erik.refresh_from_db()
    assert erik.email == "Erik@Example.com"
    assert len(mail.outbox) == 1


def test_after_the_change_only_the_new_email_signs_in(client, erik):
    client.force_login(erik)
    request_email_change(client)
    client.post(confirm_link(mail.outbox[0]))
    client.logout()

    sign_in(client, "Erik@Example.com", "erik-pass-123")
    assert not signed_in_user(client).is_authenticated

    sign_in(client, "erik.new@example.org", "erik-pass-123")
    assert signed_in_user(client) == erik
