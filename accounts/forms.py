from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from .models import Address, User


class SignupForm(UserCreationForm):
    """Django's stock signup fields plus a required email.

    The core platform asked for no email here ("signing up asks for the
    minimum"); the Account Security Center reverses that, since an account
    with no email cannot recover a forgotten password. Requiring it is this
    form's rule, not the database's — accounts made elsewhere may lack one.

    Usernames may not contain "@", so sign-in can tell a username from an
    email. The widgets carry DaisyUI classes because plain Django forms own
    their own styling here.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        # Django's stock help text still offers "@".
        username = self.fields["username"]
        username.help_text = (
            "150 characters or fewer. Letters, digits and ./+/-/_ only."
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def clean_username(self):
        username = super().clean_username()
        if "@" in username:
            raise forms.ValidationError(
                'Usernames cannot contain "@", so they are never mistaken '
                "for an email address when you sign in."
            )
        return username

    def clean_email(self):
        # A friendly field error ahead of the database's unique constraint.
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with that email already exists. "
                "Sign in, or reset your password."
            )
        return email


class SignInForm(AuthenticationForm):
    """The stock authentication form, dressed in DaisyUI.

    The username field takes an email too; ``EmailOrUsernameBackend`` in
    ``accounts.backends`` does the matching.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Username or email"
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class ChangePasswordForm(PasswordChangeForm):
    """The stock password-change form, dressed in DaisyUI.

    Django's form already checks the current password, matches the new one
    against its confirmation, and runs ``AUTH_PASSWORD_VALIDATORS``.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class ForgotPasswordForm(PasswordResetForm):
    """The stock password-reset request form, minus superusers.

    Django already matches the email ignoring case and skips inactive users
    and unusable passwords. Superusers are skipped too: whoever controls the
    admin's inbox must not be able to take over the store, so the admin
    recovers with ``manage.py changepassword`` instead. The page says the
    same thing either way, so nobody learns whose email is on file.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def get_users(self, email):
        return (user for user in super().get_users(email) if not user.is_superuser)


class SetNewPasswordForm(SetPasswordForm):
    """The stock set-password form from a reset link, dressed in DaisyUI.

    Django's form matches the new password against its confirmation and
    runs ``AUTH_PASSWORD_VALIDATORS``.
    """

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
