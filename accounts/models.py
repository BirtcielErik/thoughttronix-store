from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models, transaction


class User(AbstractUser):
    """The store's user model.

    Roles use Django's own vocabulary and nothing else: customers are
    plain users, employees are ``is_staff``, the admin is ``is_superuser``.
    """

    # Nullable per the PRD: an absent job title is unknown, not empty.
    job_title = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001


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
