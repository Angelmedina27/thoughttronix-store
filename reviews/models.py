from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from orders.models import Order, OrderItem
from products.models import Product

# Saves within this window of creation don't mark a review as edited.
EDIT_GRACE = timedelta(seconds=60)


class ReviewQuerySet(models.QuerySet):
    def visible(self):
        """Reviews shoppers may see — every listing, average, and count."""
        return self.filter(is_hidden=False)

    def hidden(self):
        """Reviews staff have hidden — the back office's moderation filter."""
        return self.filter(is_hidden=True)

    def rating_summary(self):
        """The average rating and review count, as ``{"average", "count"}``.

        ``average`` is ``None`` when there are no reviews.
        """
        return self.aggregate(average=models.Avg("rating"), count=models.Count("pk"))


class ReviewManager(models.Manager.from_queryset(ReviewQuerySet)):
    def can_create(self, user, product):
        """Whether ``user`` may write a new review of ``product``.

        The one eligibility rule: a signed-in, non-staff user with a
        delivered order line for the product and no review of it yet.
        Checked only at creation — a review stays if its order later
        changes status.
        """
        if not user.is_authenticated or user.is_staff:
            return False
        if self.filter(user=user, product=product).exists():
            return False
        return OrderItem.objects.filter(
            order__user=user,
            order__status=Order.Status.DELIVERED,
            product=product,
        ).exists()


class Review(models.Model):
    """A verified buyer's star rating and comment on one product.

    One per customer per product. Staff moderate by hiding, never by
    deleting, so a moderation mistake is reversible.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    is_hidden = models.BooleanField(default=False)

    # default (not auto_now_add) so the seed can backdate reviews, as on Order.
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ReviewManager()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"], name="unique_review_per_user_product"
            )
        ]

    def __str__(self):
        return f"{self.rating}★ {self.product.name} by {self.user.username}"

    @property
    def edited(self):
        """Whether the review was saved again more than a minute after posting."""
        return self.updated_at - self.created_at > EDIT_GRACE
