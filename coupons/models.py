"""Coupons: seasonal discount codes that marketing runs from the back office.

A coupon takes a percentage or a fixed amount off either the whole order
or one product's cart line; a fixed amount on a product comes off each
unit in the line. Every rule about whether a code applies, and
how much it takes off, lives on the model: the checkout preview, the
checkout form, and ``place_order`` all ask ``Coupon.discount_for`` and
nothing else.

Imports flow one way: ``orders`` depends on ``coupons``, never the
reverse. Where a coupon needs its orders (usage counts, the
once-per-customer rule) it reaches them through the ``orders`` reverse
relation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Count, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.formats import date_format

from products.models import Product

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from orders.models import Cart

CENT = Decimal("0.01")
ZERO = Decimal("0.00")

# ``orders.Order.Status.CANCELLED``, spelled out: importing ``orders`` here
# would make the dependency circular. A cancelled order never counts as a
# use of its coupon.
CANCELLED = "CANCELLED"

code_validator = RegexValidator(
    r"^[A-Za-z0-9-]+$", "Use letters, digits, and hyphens only."
)


def normalize_code(code: str) -> str:
    """Codes are case-insensitive: stored and compared trimmed and uppercase."""
    return code.strip().upper()


class CouponError(ValueError):
    """A code that can't be applied. The message is written for the customer.

    A ``ValueError``, so ``place_order``'s documented contract ("raises
    ``ValueError``") still holds, while callers can catch coupon failures
    on their own.
    """


@dataclass(frozen=True)
class Discount:
    """What one coupon takes off one cart."""

    coupon: Coupon
    amount: Decimal
    # The product whose line the discount lands on; None when order-wide.
    product: Product | None

    @property
    def product_id(self) -> int | None:
        return self.product.pk if self.product else None


class CouponQuerySet(models.QuerySet):
    def lookup(self, code: str) -> Coupon:
        """The coupon for a code as a customer typed it.

        Raises ``CouponError`` when no such code exists.
        """
        try:
            return self.select_related("product").get(code=normalize_code(code))
        except self.model.DoesNotExist:
            raise CouponError("We don't recognize that code.") from None

    def with_usage(self) -> CouponQuerySet:
        """Annotate ``uses`` and ``discounted`` over non-cancelled orders."""
        counted = ~Q(orders__status=CANCELLED)
        return self.annotate(
            uses=Count("orders", filter=counted),
            discounted=Coalesce(
                Sum("orders__discount", filter=counted),
                Value(ZERO),
                output_field=models.DecimalField(max_digits=12, decimal_places=2),
            ),
        )


class Coupon(models.Model):
    """A discount code. Coupons are retired (``is_active=False``), never deleted.

    Scope follows ``product``: blank means the whole order, set means that
    one product's cart line. A code is usable while it is active and today
    (store time) falls inside its optional, inclusive date window.
    """

    class Kind(models.TextChoices):
        PERCENT = "PERCENT", "Percent off"
        AMOUNT = "AMOUNT", "Amount off"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        SCHEDULED = "SCHEDULED", "Scheduled"
        EXPIRED = "EXPIRED", "Expired"
        RETIRED = "RETIRED", "Retired"

    # What the coupon gives. Locked once an order has used it, so the
    # coupon always describes every order that carries it. The schedule
    # (is_active and the dates) and the description stay editable.
    TERMS = ["code", "kind", "value", "product", "min_spend"]

    code = models.CharField(
        max_length=30,
        unique=True,
        validators=[code_validator],
        help_text="What customers type. Not case-sensitive.",
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        help_text="For staff only, e.g. the campaign it belongs to.",
    )
    kind = models.CharField(max_length=7, choices=Kind.choices, default=Kind.PERCENT)
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(CENT)],
        help_text=(
            "A percentage (1–100) or a dollar amount, depending on the kind. "
            "Dollar amounts on a product coupon come off each unit."
        ),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="coupons",
        help_text="Leave blank to discount the whole order.",
    )
    min_spend = models.DecimalField(
        "minimum spend",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(CENT)],
        help_text="Optional. The cart subtotal must reach this amount.",
    )
    is_active = models.BooleanField(
        "active",
        default=True,
        help_text="Switch off to retire the code immediately.",
    )
    starts_on = models.DateField(
        null=True, blank=True, help_text="Optional. First day the code works."
    )
    ends_on = models.DateField(
        null=True, blank=True, help_text="Optional. Last day the code works."
    )
    created_at = models.DateTimeField(default=timezone.now)

    objects = CouponQuerySet.as_manager()

    class Meta:
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(
                condition=Q(value__gt=0), name="coupon_value_positive"
            ),
            models.CheckConstraint(
                condition=Q(kind="AMOUNT") | Q(value__lte=100),
                name="coupon_percent_at_most_100",
            ),
            models.CheckConstraint(
                condition=Q(starts_on__isnull=True)
                | Q(ends_on__isnull=True)
                | Q(ends_on__gte=F("starts_on")),
                name="coupon_window_in_order",
            ),
        ]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = normalize_code(self.code)
        super().save(*args, **kwargs)

    def clean(self):
        # Normalized here too, so the uniqueness check that follows sees
        # the stored form: "fall15" collides with "FALL15".
        self.code = normalize_code(self.code or "")
        errors = {}
        if self.kind == self.Kind.PERCENT and self.value and self.value > 100:
            errors["value"] = "A percentage can't be more than 100."
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            errors["ends_on"] = "The last day can't be before the first day."
        if errors:
            raise ValidationError(errors)
        if self.pk and self.has_been_used():
            saved = type(self).objects.get(pk=self.pk)
            changed = [
                name
                for name in self.TERMS
                if getattr(saved, self._meta.get_field(name).attname)
                != getattr(self, self._meta.get_field(name).attname)
            ]
            if changed:
                raise ValidationError(
                    "This code has been used, so its terms are locked. "
                    "Create a new code instead."
                )

    @property
    def status(self) -> str:
        """Active, scheduled, expired, or retired, as of today in store time."""
        today = timezone.localdate()
        if not self.is_active:
            return self.Status.RETIRED
        if self.starts_on and today < self.starts_on:
            return self.Status.SCHEDULED
        if self.ends_on and today > self.ends_on:
            return self.Status.EXPIRED
        return self.Status.ACTIVE

    def get_status_display(self) -> str:
        return self.Status(self.status).label

    @property
    def summary(self) -> str:
        """The offer in words, e.g. "15% off the whole order"."""
        if self.kind == self.Kind.PERCENT:
            amount = f"{self.value.normalize():f}%"
        else:
            amount = f"${self.value:,.2f}"
        if self.product is None:
            target = "the whole order"
        elif self.kind == self.Kind.AMOUNT:
            target = f"each {self.product.name}"
        else:
            target = self.product.name
        return f"{amount} off {target}"

    def has_been_used(self) -> bool:
        """Whether any order, cancelled or not, carries this coupon."""
        return self.orders.exists()

    def amount_off(self, base: Decimal, *, units: int = 1) -> Decimal:
        """The discount on ``base``: rounded to the cent, never more than ``base``.

        ``base`` is the cart subtotal for an order-wide coupon, or the
        targeted product's line total for an item coupon. ``units`` is that
        line's quantity: a fixed amount comes off each unit, so item-coupon
        callers must pass it. A percentage ignores it (a share of the line
        already covers every unit), and an order-wide coupon applies once,
        so its callers leave it at 1.
        """
        if self.kind == self.Kind.PERCENT:
            amount = (base * self.value / 100).quantize(CENT, rounding=ROUND_HALF_UP)
        else:
            amount = self.value * units
        return min(amount, base)

    def discount_for(self, cart: Cart, user: AbstractBaseUser) -> Discount:
        """What this coupon takes off ``cart`` for ``user``.

        Raises ``CouponError``, with a message for the customer, when the
        code is retired, outside its dates, already used by this customer
        on a non-cancelled order, aimed at a product not in the cart, or
        short of its minimum spend (measured against the cart subtotal).
        """
        status = self.status
        if status == self.Status.RETIRED:
            raise CouponError(f"{self.code} is no longer valid.")
        if status == self.Status.SCHEDULED:
            starts = date_format(self.starts_on, "F j, Y")
            raise CouponError(f"{self.code} isn't valid until {starts}.")
        if status == self.Status.EXPIRED:
            ended = date_format(self.ends_on, "F j, Y")
            raise CouponError(f"{self.code} expired on {ended}.")
        if self.orders.filter(user=user).exclude(status=CANCELLED).exists():
            raise CouponError(f"You've already used {self.code}.")

        subtotal = cart.total()
        if self.product_id is None:
            base, units = subtotal, 1
        else:
            line = next(
                (line for line in cart.lines() if line.product_id == self.product_id),
                None,
            )
            if line is None:
                raise CouponError(
                    f"{self.code} applies to {self.product.name}, "
                    "which isn't in your cart."
                )
            base, units = line.line_total, line.quantity
        if self.min_spend and subtotal < self.min_spend:
            raise CouponError(
                f"{self.code} needs an order of at least ${self.min_spend:,.2f}."
            )
        return Discount(
            coupon=self,
            amount=self.amount_off(base, units=units),
            product=self.product,
        )
