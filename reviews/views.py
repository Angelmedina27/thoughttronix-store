"""Customer review views — ordinary multi-page form flows, not HTMX.

Public URLs are keyed by product slug, like the catalog. Every entry
point defers to ``Review.objects.can_create`` for eligibility.
"""

from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DeleteView, ListView, UpdateView, View

from accounts.mixins import StaffRequiredMixin
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


class ReviewDeleteView(UserPassesTestMixin, DeleteView):
    """Delete a review after a confirmation page, then return to its product.

    Only the author may delete, and only while the review is visible.
    Anonymous users are sent to sign in; anyone else gets 403.
    """

    model = Review

    def test_func(self):
        return self.get_object().can_be_deleted_by(self.request.user)

    def form_valid(self, form):
        product = self.object.product
        self.object.delete()
        messages.success(self.request, "Done — your review is deleted.")
        return redirect(product)


# --- Back office ---------------------------------------------------------------
# Staff moderate reviews; they never write or edit them. URLs use pks per the
# URL conventions, and ``section`` drives the active tab in the staff shell.


class ManageReviewListView(StaffRequiredMixin, ListView):
    """Every review, hidden ones included, newest first.

    ``?hidden=1`` narrows the list to hidden reviews, so staff can revisit
    past moderation decisions.
    """

    template_name = "reviews/manage_reviews.html"
    context_object_name = "reviews"
    extra_context = {"section": "reviews"}

    def get_queryset(self):
        reviews = Review.objects.select_related("user", "product")
        if self.hidden_only:
            reviews = reviews.hidden()
        return reviews

    @property
    def hidden_only(self):
        return self.request.GET.get("hidden") == "1"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["hidden_only"] = self.hidden_only
        return context


class ToggleReviewHiddenView(StaffRequiredMixin, View):
    """HTMX, POST-only: hide or unhide a review, then re-render its row.

    The only change staff can make to a review — never its text or rating.
    """

    def post(self, request, pk):
        review = get_object_or_404(
            Review.objects.select_related("user", "product"), pk=pk
        )
        review.toggle_hidden()
        return render(request, "reviews/partials/_review_row.html", {"review": review})
