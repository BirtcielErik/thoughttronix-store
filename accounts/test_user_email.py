import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor

# --- The email rule at the database ------------------------------------------


def test_second_email_differing_only_in_case_is_rejected_by_the_database(db):
    User = get_user_model()
    User.objects.create_user(username="erik", email="erik@example.com")

    with pytest.raises(IntegrityError):
        User.objects.create_user(username="erik2", email="Erik@Example.com")


def test_email_is_stored_as_typed(db):
    user = get_user_model().objects.create_user(
        username="erik", email="Erik@Example.com"
    )

    user.refresh_from_db()
    assert user.email == "Erik@Example.com"


def test_users_without_email_coexist_as_null(db):
    User = get_user_model()
    User.objects.create_user(username="first")
    User.objects.create_user(username="second", email="")
    User.objects.create(username="third")

    assert User.objects.filter(email__isnull=True).count() == 3
    assert not User.objects.filter(email="").exists()


def test_superuser_can_be_created_without_email(db):
    admin = get_user_model().objects.create_superuser(
        username="admin", email="", password="x"
    )

    admin.refresh_from_db()
    assert admin.email is None


def test_full_clean_reports_the_email_clash(db):
    # The Django admin validates through full_clean, so the constraint's
    # message is what a staff member sees there.
    User = get_user_model()
    User.objects.create_user(username="erik", email="erik@example.com")
    clash = User(username="erik2", email="ERIK@example.com")
    clash.set_unusable_password()

    with pytest.raises(ValidationError, match="email already exists"):
        clash.full_clean()


# --- The migration's data step ------------------------------------------------

BEFORE = [("accounts", "0002_address")]
AFTER = [("accounts", "0003_user_email_unique_nullable")]


@pytest.mark.django_db(transaction=True)
def test_migration_turns_blank_emails_into_null():
    executor = MigrationExecutor(connection)
    executor.migrate(BEFORE)
    old_apps = executor.loader.project_state(BEFORE).apps
    OldUser = old_apps.get_model("accounts", "User")
    # Two accounts from the old, email-less sign-up: both hold "".
    OldUser.objects.create(username="legacy-one", email="")
    OldUser.objects.create(username="legacy-two", email="")
    OldUser.objects.create(username="has-email", email="Has@Example.com")

    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(AFTER)

    User = get_user_model()
    assert User.objects.get(username="legacy-one").email is None
    assert User.objects.get(username="legacy-two").email is None
    assert User.objects.get(username="has-email").email == "Has@Example.com"
