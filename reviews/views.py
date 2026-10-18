"""Customer review views — ordinary multi-page form flows, not HTMX.

Public URLs are keyed by product slug, like the catalog. Every entry
point defers to ``Review.objects.can_create`` for eligibility.
"""

from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import UpdateView

from products.models import Product

from .forms import ReviewForm
from .models import Review


class ReviewWriteView(UserPassesTestMixin, UpdateView):
    """Write a review of one product, or edit the one already written.

    One URL per product: if the user has a review of it, this is its edit
    form, gated on ownership alone; otherwise it is the create form, gated
    on eligibility. Anonymous users are sent to sign in; signed-in users
    who may do neither get 403 (``AccessMixin``'s default split).
    """

    model = Review
    form_class = ReviewForm
    template_name = "reviews/review_form.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.product = get_object_or_404(Product, slug=kwargs["slug"])
        self.review = (
            Review.objects.filter(user=request.user, product=self.product).first()
            if request.user.is_authenticated
            else None
        )

    def test_func(self):
        if self.review is not None:
            return True
        return Review.objects.can_create(self.request.user, self.product)

    def get_object(self, queryset=None):
        # None makes the form a create form.
        return self.review

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product"] = self.product
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.product = self.product
        form.save()
        if self.review is None:
            messages.success(self.request, "Thanks — your review is live.")
        else:
            messages.success(self.request, "Thanks — your review is updated.")
        return redirect(self.product)
