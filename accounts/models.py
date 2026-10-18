from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.core import signing
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models.functions import Lower
from django.utils.crypto import constant_time_compare, salted_hmac

# --- Email-change confirmation tokens ---------------------------------------
#
# Stateless: nothing about a pending change is stored. The signed payload
# names the account, the new email, the email current when the change was
# requested, and a fingerprint of the password hash. Confirming changes the
# email, so a link works once; changing the password changes the hash, so it
# cancels every link not yet confirmed.

EMAIL_CHANGE_SALT = "accounts.User.email_change"

# One hour, like PASSWORD_RESET_TIMEOUT: long enough to reach an inbox, short
# enough that a stale link is useless.
EMAIL_CHANGE_MAX_AGE = 60 * 60


def _password_fingerprint(user):
    # An HMAC rather than the hash itself: a signed payload is readable by
    # anyone holding the link.
    return salted_hmac(EMAIL_CHANGE_SALT, user.password).hexdigest()


class UserManager(DjangoUserManager):
    @classmethod
    def normalize_email(cls, email):
        """The email as typed, or None when there is none — never "".

        Django's version lowercases the domain and turns a missing email
        into "". Both ``create_user`` and ``AbstractUser.clean`` call it,
        so this is the one place that keeps the stored email as typed and
        a missing one NULL. Matching ignores case anyway.
        """
        return email or None

    def from_email_change_token(self, token):
        """The ``(user, new_email)`` a confirmation token names, or None.

        None covers every reason a link is dead — expired, tampered, the
        email already changed since the request, the password changed since
        the request, or the account deactivated — so the page can say one
        thing for all of them.
        """
        try:
            payload = signing.loads(
                token, salt=EMAIL_CHANGE_SALT, max_age=EMAIL_CHANGE_MAX_AGE
            )
        except signing.BadSignature:
            return None
        user = self.filter(pk=payload["user"], is_active=True).first()
        if (
            user is None
            or user.email != payload["old"]
            or not constant_time_compare(_password_fingerprint(user), payload["pw"])
        ):
            return None
        return user, payload["new"]


class User(AbstractUser):
    """The store's user model.

    Roles use Django's own vocabulary and nothing else: customers are
    plain users, employees are ``is_staff``, the admin is ``is_superuser``.

    Each email belongs to at most one account, ignoring capitalization.
    Sign-up requires one; accounts made elsewhere (the Django admin,
    ``createsuperuser``, the shell, ``seed``) may have none.
    """

    # Nullable so accounts without an email are NULL, never "" — two
    # empty strings would collide under the case-insensitive unique
    # constraint below, while NULLs never do. Stored as typed.
    email = models.EmailField("email address", null=True, blank=True)  # noqa: DJ001

    # Nullable per the PRD: an absent job title is unknown, not empty.
    job_title = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="unique_user_email_ci",
                violation_error_message="A user with that email already exists.",
            ),
        ]

    @property
    def public_name(self):
        """The name shown on public pages: first name and last initial.

        "Nova K." — never the full name. Falls back to the username when
        no first name is on file.
        """
        first = self.first_name.strip()
        if not first:
            return self.username
        initial = self.last_name.strip()[:1]
        return f"{first} {initial}." if initial else first

    def make_email_change_token(self, new_email):
        """A signed, one-hour token that confirms a change to ``new_email``.

        ``UserManager.from_email_change_token`` reads it back.
        """
        return signing.dumps(
            {
                "user": self.pk,
                "new": new_email,
                "old": self.email,
                "pw": _password_fingerprint(self),
            },
            salt=EMAIL_CHANGE_SALT,
        )


# --- Postal vocabulary ------------------------------------------------------
#
# Shared by the saved-address model below and by orders' CheckoutForm.
# It lives here, with the model that stores an address, so the dependency
# runs one way — orders imports accounts, never the reverse.

US_STATES = [
    ("AL", "Alabama"),
    ("AK", "Alaska"),
    ("AZ", "Arizona"),
    ("AR", "Arkansas"),
    ("CA", "California"),
    ("CO", "Colorado"),
    ("CT", "Connecticut"),
    ("DE", "Delaware"),
    ("DC", "District of Columbia"),
    ("FL", "Florida"),
    ("GA", "Georgia"),
    ("HI", "Hawaii"),
    ("ID", "Idaho"),
    ("IL", "Illinois"),
    ("IN", "Indiana"),
    ("IA", "Iowa"),
    ("KS", "Kansas"),
    ("KY", "Kentucky"),
    ("LA", "Louisiana"),
    ("ME", "Maine"),
    ("MD", "Maryland"),
    ("MA", "Massachusetts"),
    ("MI", "Michigan"),
    ("MN", "Minnesota"),
    ("MS", "Mississippi"),
    ("MO", "Missouri"),
    ("MT", "Montana"),
    ("NE", "Nebraska"),
    ("NV", "Nevada"),
    ("NH", "New Hampshire"),
    ("NJ", "New Jersey"),
    ("NM", "New Mexico"),
    ("NY", "New York"),
    ("NC", "North Carolina"),
    ("ND", "North Dakota"),
    ("OH", "Ohio"),
    ("OK", "Oklahoma"),
    ("OR", "Oregon"),
    ("PA", "Pennsylvania"),
    ("RI", "Rhode Island"),
    ("SC", "South Carolina"),
    ("SD", "South Dakota"),
    ("TN", "Tennessee"),
    ("TX", "Texas"),
    ("UT", "Utah"),
    ("VT", "Vermont"),
    ("VA", "Virginia"),
    ("WA", "Washington"),
    ("WV", "West Virginia"),
    ("WI", "Wisconsin"),
    ("WY", "Wyoming"),
]

zip_validator = RegexValidator(
    r"^\d{5}(-\d{4})?$", "Enter a ZIP code like 79016 or 79016-1234."
)

# The two address slots a checkout has, and the field-name mapping between
# them and this model. The checkout calls it ``shipping_zip``; the model
# calls it ``zip_code``, so the names are mapped rather than assumed equal.
SLOTS = ("shipping", "billing")

CHECKOUT_PARTS = {
    "name": "name",
    "street": "street",
    "line2": "line2",
    "city": "city",
    "state": "state",
    "zip": "zip_code",
}


class AddressManager(models.Manager):
    """Address creation that knows how to read a checkout."""

    def remember(self, user, checkout_data, slot):
        """Save one slot of a checkout as an address, reusing an identical one.

        Idempotent by design: a customer who picks a saved address and then
        ticks "save this address" gets the row they already had, not a
        duplicate. This runs inside ``place_order``'s transaction, so it
        must never raise on ordinary input — a unique constraint here would
        cost the customer their order.
        """
        fields = {
            attr: checkout_data[f"{slot}_{suffix}"]
            for suffix, attr in CHECKOUT_PARTS.items()
        }
        address, _ = self.get_or_create(user=user, **fields)
        return address


class Address(models.Model):
    """A shipping or billing address a customer has saved for reuse.

    Untyped on purpose: an address is not intrinsically a shipping or a
    billing address — it becomes one by being chosen for a slot at
    checkout. The two ``is_default_*`` flags are what remember the usual
    choice, one of each per customer.

    Orders never point here. ``Order`` keeps its own flat copy of every
    address field, so editing or deleting a saved address leaves order
    history untouched.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    label = models.CharField(
        max_length=50,
        blank=True,
        help_text="Optional — something like Home or Work.",
    )

    name = models.CharField("Full name", max_length=100)
    street = models.CharField("Street address", max_length=200)
    line2 = models.CharField("Apt, suite, etc.", max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2, choices=US_STATES)
    zip_code = models.CharField("ZIP code", max_length=10, validators=[zip_validator])

    is_default_shipping = models.BooleanField(default=False)
    is_default_billing = models.BooleanField(default=False)

    objects = AddressManager()

    class Meta:
        verbose_name_plural = "addresses"
        ordering = ["-is_default_shipping", "-is_default_billing", "street"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default_shipping=True),
                name="one_default_shipping_address_per_user",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default_billing=True),
                name="one_default_billing_address_per_user",
            ),
        ]

    def __str__(self):
        """The label if the customer gave one, else the address itself."""
        return self.label or f"{self.street}, {self.city} {self.state}"

    def as_initial(self, slot):
        """This address as ``CheckoutForm`` initial data for one slot.

        ``as_initial("shipping")`` returns ``{"shipping_name": ...}`` —
        the keys the checkout form's shipping fields are named after.
        """
        return {
            f"{slot}_{suffix}": getattr(self, attr)
            for suffix, attr in CHECKOUT_PARTS.items()
        }

    def apply_defaults(self, *, shipping, billing):
        """Set both default flags, clearing whichever address is displaced.

        Only one address per customer may hold each flag — a database
        constraint enforces it — so the previous holder is cleared first.
        The row must already be saved; an unsaved one has no pk to exclude.
        """
        with transaction.atomic():
            for slot, wanted in (("shipping", shipping), ("billing", billing)):
                field = f"is_default_{slot}"
                if wanted:
                    self.user.addresses.exclude(pk=self.pk).filter(
                        **{field: True}
                    ).update(**{field: False})
                setattr(self, field, wanted)
            self.save(update_fields=["is_default_shipping", "is_default_billing"])
