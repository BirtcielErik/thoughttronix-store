from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Address, User


class SignupForm(UserCreationForm):
    """Django's stock signup fields — username plus password and confirmation.

    No email: signing up asks for the minimum. The widgets carry DaisyUI
    classes because plain Django forms own their own styling here.
    """

    class Meta(UserCreationForm.Meta):
        model = User

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class SignInForm(AuthenticationForm):
    """The stock authentication form, dressed in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class AddressForm(forms.ModelForm):
    """A saved address, with its two default flags alongside.

    The flags are declared here rather than in ``Meta.fields`` on purpose.
    A ModelForm assigns its Meta fields straight onto the instance, and
    saving an instance that claims a flag another address already holds
    would break the one-default-per-customer constraints. The view saves
    the row first and then hands the flags to ``Address.apply_defaults``,
    which clears the displaced address in the same transaction.
    """

    is_default_shipping = forms.BooleanField(
        label="Use as my default shipping address", required=False
    )
    is_default_billing = forms.BooleanField(
        label="Use as my default billing address", required=False
    )

    class Meta:
        model = Address
        fields = ["label", "name", "street", "line2", "city", "state", "zip_code"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Outside Meta.fields, so model_to_dict never seeds these.
            self.fields[
                "is_default_shipping"
            ].initial = self.instance.is_default_shipping
            self.fields["is_default_billing"].initial = self.instance.is_default_billing
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "toggle toggle-primary"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            else:
                widget.attrs["class"] = "input w-full"
