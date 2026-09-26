from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import AddressForm, SignInForm, SignupForm
from .models import Address


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
