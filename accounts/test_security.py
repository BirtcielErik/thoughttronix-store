"""Sign-in by username or email, the Security Center hub, and its actions."""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import get_hasher
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
