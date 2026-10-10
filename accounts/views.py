from django.conf import settings
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    AddressForm,
    ChangeEmailForm,
    ChangePasswordForm,
    ForgotPasswordForm,
    SetNewPasswordForm,
    SignInForm,
    SignupForm,
)
from .models import Address, User


class SignupView(SuccessMessageMixin, CreateView):
    """Create a customer account, then hand off to the login page.

    New users sign in themselves — auto-login after signup is left as a
    student exercise.
    """

    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:login")
    success_message = "Account created — you can now sign in."


class SignInView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = SignInForm


class SignOutView(LogoutView):
    def post(self, request, *args, **kwargs):
        # Flash after super() has flushed the session, or the message
        # would be wiped along with it.
        response = super().post(request, *args, **kwargs)
        messages.info(request, "You have signed out.")
        return response


# --- Security Center ----------------------------------------------------------
#
# Shaped like the address book: a hub page, plus separate form pages that
# redirect back here with a flash message. Every signed-in user gets it —
# customers, employees and the superuser alike — so there are no role checks.


class SecurityView(LoginRequiredMixin, TemplateView):
    """The Security Center hub: the account's username and email."""

    template_name = "accounts/security.html"


def send_password_changed_notice(user):
    """Tell the account's inbox its password changed; skip if none is on file.

    Sent from the view that completes the change, and from no service
    module: it touches one model. ``from_email`` is left to
    ``DEFAULT_FROM_EMAIL``, the ThoughtTronix sender.
    """
    if not user.email:
        return
    send_mail(
        "Your ThoughtTronix password was changed",
        render_to_string("accounts/email/password_changed.txt", {"user": user}),
        None,
        [user.email],
    )


class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    """Django's password change, which already requires sign-in.

    Django re-hashes this session's auth hash so the user stays signed in
    here, and every other session for the account fails its hash check and
    is signed out.
    """

    form_class = ChangePasswordForm
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:security")
    success_message = "Password changed. You've been signed out everywhere else."

    def form_valid(self, form):
        response = super().form_valid(form)
        send_password_changed_notice(form.user)
        return response


def mask_email(email):
    """``n***@example.com``: enough for the owner to recognize, no more."""
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


class ChangeEmailView(LoginRequiredMixin, FormView):
    """Request an email change; the account's email stays as it is.

    A signed link goes to the new address, and only opening it and pressing
    confirm (``ConfirmEmailView``) makes the change, so a typo in the new
    address cannot quietly break password recovery.
    """

    form_class = ChangeEmailForm
    template_name = "accounts/email_change.html"
    success_url = reverse_lazy("accounts:security")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        new_email = form.cleaned_data["email"]
        token = user.make_email_change_token(new_email)
        link = self.request.build_absolute_uri(
            reverse("accounts:email_confirm", kwargs={"token": token})
        )
        send_mail(
            "Confirm your new ThoughtTronix email",
            render_to_string(
                "accounts/email/email_change_confirm.txt",
                {"user": user, "new_email": new_email, "link": link},
            ),
            None,
            [new_email],
        )
        messages.success(self.request, f"Check {new_email} for a confirmation link.")
        return super().form_valid(form)


class ConfirmEmailView(TemplateView):
    """Apply an email change from its emailed link.

    No sign-in needed: the signed token alone names the account and the
    change, so the link works from a phone that has never signed in. A GET
    only shows the change; the POST behind the confirm button makes it, so
    a mail scanner that opens links cannot confirm one.
    """

    template_name = "accounts/email_confirm.html"

    def dispatch(self, request, *args, **kwargs):
        found = User.objects.from_email_change_token(kwargs["token"])
        self.account, self.new_email = found or (None, None)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["validlink"] = self.account is not None
        context["new_email"] = self.new_email
        return context

    def post(self, request, *args, **kwargs):
        if self.account is None:
            return self.get(request, *args, **kwargs)
        # Checked again: the address may have been claimed since the request.
        if User.objects.filter(email__iexact=self.new_email).exists():
            return self.render_to_response(
                self.get_context_data(
                    error="That email is now in use by another account."
                )
            )
        old_email = self.account.email
        self.account.email = self.new_email
        self.account.save(update_fields=["email"])
        if old_email:
            send_mail(
                "Your ThoughtTronix email was changed",
                render_to_string(
                    "accounts/email/email_changed.txt",
                    {"user": self.account, "masked_email": mask_email(self.new_email)},
                ),
                None,
                [old_email],
            )
        messages.success(request, f"Your email is now {self.new_email}.")
        if request.user.pk == self.account.pk:
            return redirect("accounts:security")
        return redirect(settings.LOGIN_URL)


# --- Forgot password ----------------------------------------------------------
#
# Django's four password-reset views, moved into the accounts namespace (their
# default success URLs name un-namespaced routes) and dressed in DaisyUI. The
# link lifetime is PASSWORD_RESET_TIMEOUT in settings.


class PasswordResetView(auth_views.PasswordResetView):
    """Ask for an email and send a reset link if it matches an account.

    The next page is the same whether or not anything was sent.
    """

    form_class = ForgotPasswordForm
    template_name = "accounts/password_reset_form.html"
    subject_template_name = "accounts/email/password_reset_subject.txt"
    email_template_name = "accounts/email/password_reset.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(
    SuccessMessageMixin, auth_views.PasswordResetConfirmView
):
    """Choose a new password from a reset link.

    Django's token dies once the password changes, so a link works once.
    Saving the password also fails every existing session's auth hash, which
    signs the account out everywhere; this view does not sign it back in.
    """

    form_class = SetNewPasswordForm
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")
    success_message = "Your password has been reset. Sign in with your new password."

    def form_valid(self, form):
        response = super().form_valid(form)
        send_password_changed_notice(form.user)
        return response


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    """Hand off to the sign-in page, where the success message shows.

    The message is set by the confirm view, which knows a reset happened, so
    opening this URL directly flashes nothing.
    """

    def get(self, request, *args, **kwargs):
        return redirect(settings.LOGIN_URL)


# --- Saved addresses --------------------------------------------------------
#
# The customer's own address book, reused by the checkout picker. Every
# view reaches an address through its owner, never by bare pk — the same
# rule orders follow, and the one that keeps a stranger's home address
# out of reach of a guessed URL.


class OwnAddressesMixin(LoginRequiredMixin):
    """Addresses are always fetched through the owner — never by bare pk."""

    model = Address

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressListView(OwnAddressesMixin, ListView):
    """The customer's address book."""

    template_name = "accounts/address_list.html"
    context_object_name = "addresses"

    def get_queryset(self):
        return super().get_queryset().order_by("label")


class AddressFormMixin(OwnAddressesMixin, SuccessMessageMixin):
    """Shared plumbing for adding and editing an address."""

    form_class = AddressForm
    template_name = "accounts/address_form.html"
    success_url = reverse_lazy("accounts:addresses")

    def form_valid(self, form):
        form.instance.user = self.request.user
        # Save with the flags down, then apply them: apply_defaults has to
        # clear the address it displaces, and it needs a saved row to do it.
        form.instance.is_default_shipping = False
        form.instance.is_default_billing = False
        response = super().form_valid(form)
        self.object.apply_defaults(
            shipping=form.cleaned_data["is_default_shipping"],
            billing=form.cleaned_data["is_default_billing"],
        )
        return response


class AddressCreateView(AddressFormMixin, CreateView):
    success_message = "Address saved."


class AddressUpdateView(AddressFormMixin, UpdateView):
    success_message = "Address updated."


class AddressDeleteView(OwnAddressesMixin, SuccessMessageMixin, DeleteView):
    """Hard delete, behind a confirmation page.

    Past orders are unaffected: an ``Order`` holds its own flat copy of
    every address field and no foreign key to here.
    """

    template_name = "accounts/address_confirm_delete.html"
    context_object_name = "address"
    success_url = reverse_lazy("accounts:addresses")
    success_message = "Address deleted."
