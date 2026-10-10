"""Sign-in by username or email, and the Security Center hub."""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import get_hasher
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
