"""The back office's Coupons tab: marketing creates, schedules, and retires codes.

Staff-only like every back-office screen (any staff member may manage
coupons). There is no delete view: a coupon is retired, never deleted,
so its history stays. The ``section`` context entry drives the active
tab in the staff shell.
"""

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.mixins import StaffRequiredMixin

from .forms import CouponForm
from .models import Coupon


class ManageCouponListView(StaffRequiredMixin, ListView):
    """Every coupon, with its status and how much it has been used."""

    template_name = "coupons/manage_coupons.html"
    context_object_name = "coupons"
    extra_context = {"section": "coupons"}

    def get_queryset(self):
        # Explicit: Meta.ordering is dropped from aggregate (GROUP BY) queries.
        return Coupon.objects.select_related("product").with_usage().order_by("code")


class ManageCouponDetailView(StaffRequiredMixin, DetailView):
    """One coupon's terms, schedule, and the orders that used it."""

    template_name = "coupons/manage_coupon_detail.html"
    context_object_name = "coupon"
    queryset = Coupon.objects.select_related("product").with_usage()
    extra_context = {"section": "coupons"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["orders"] = self.object.orders.select_related("user")
        return context


class ManageCouponCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = Coupon
    form_class = CouponForm
    template_name = "coupons/manage_coupon_form.html"
    success_message = "%(code)s created."
    extra_context = {"section": "coupons"}

    def get_success_url(self):
        return reverse("coupons:manage_coupon_detail", kwargs={"pk": self.object.pk})


class ManageCouponUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Coupon
    form_class = CouponForm
    template_name = "coupons/manage_coupon_form.html"
    success_message = "%(code)s saved."
    extra_context = {"section": "coupons"}

    def get_success_url(self):
        return reverse("coupons:manage_coupon_detail", kwargs={"pk": self.object.pk})


class ToggleCouponView(StaffRequiredMixin, View):
    """POST-only: retire an active code, or bring a retired one back."""

    def post(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk)
        coupon.is_active = not coupon.is_active
        coupon.save(update_fields=["is_active"])
        verb = "reactivated" if coupon.is_active else "retired"
        messages.success(request, f"{coupon.code} {verb}.")
        return redirect("coupons:manage_coupon_detail", pk=coupon.pk)
