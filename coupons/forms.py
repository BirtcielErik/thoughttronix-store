"""The back-office coupon form.

The model owns the rules (percent at most 100, the date window in order,
codes normalized and unique, terms locked once used); the form inherits
them through ``full_clean``. Its own job is presentation: date pickers,
and disabling the locked fields so staff can see why they can't change.
"""

from django import forms

from products.forms import StyledModelForm

from .models import Coupon


class CouponForm(StyledModelForm):
    class Meta:
        model = Coupon
        fields = [
            "code",
            "description",
            "kind",
            "value",
            "product",
            "min_spend",
            "starts_on",
            "ends_on",
            "is_active",
        ]
        widgets = {
            "starts_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "ends_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].empty_label = "Whole order"
        self.terms_locked = bool(self.instance.pk and self.instance.has_been_used())
        if self.terms_locked:
            # Disabled fields ignore whatever is posted and keep the saved
            # value; the model's clean() refuses a change regardless.
            for name in Coupon.TERMS:
                self.fields[name].disabled = True
