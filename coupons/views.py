"""Back-office coupon management — staff-only, pks per the URL conventions.

No delete view: retiring (``is_active=False``) is the only supported way to
end a code's life, so past orders that used it stay explainable.
"""

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from accounts.mixins import StaffRequiredMixin

from .forms import CouponForm
from .models import Coupon


class ManageCouponListView(StaffRequiredMixin, ListView):
    template_name = "coupons/manage_coupons.html"
    context_object_name = "coupons"
    extra_context = {"section": "coupons"}
    queryset = Coupon.objects.select_related("product")


class ManageCouponCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = Coupon
    form_class = CouponForm
    template_name = "coupons/manage_coupon_form.html"
    success_url = reverse_lazy("coupons:manage_coupons")
    success_message = "“%(code)s” created."
    extra_context = {"section": "coupons"}


class ManageCouponUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Coupon
    form_class = CouponForm
    template_name = "coupons/manage_coupon_form.html"
    success_url = reverse_lazy("coupons:manage_coupons")
    success_message = "“%(code)s” saved."
    extra_context = {"section": "coupons"}


class RetireCouponView(StaffRequiredMixin, View):
    """POST-only: deactivate a code without deleting its history."""

    def post(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk)
        coupon.is_active = False
        coupon.save(update_fields=["is_active"])
        messages.success(request, f"“{coupon.code}” retired.")
        return redirect("coupons:manage_coupons")
