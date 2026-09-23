"""The back-office coupon form.

Reuses ``StyledModelForm`` from ``products.forms`` — DaisyUI widget classes
shouldn't be redeclared per app. The only imperative rule, normalizing the
code's case, has to run before the model's own field validators do (they
fire during ``ModelForm._post_clean``), so it lives in ``clean_code``.
"""

from django import forms

from products.forms import StyledModelForm
from products.models import Product

from .models import Coupon


class CouponForm(StyledModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        required=False,
        empty_label="Order-wide (any product)",
    )

    class Meta:
        model = Coupon
        fields = ["code", "percent_off", "product", "expires_at", "is_active"]
        widgets = {
            "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()
