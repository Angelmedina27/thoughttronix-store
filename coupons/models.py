from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.utils import timezone

from products.models import Product

code_validator = RegexValidator(
    r"^[A-Z0-9]+$", "Use letters and numbers only, no spaces — e.g. FALL26."
)


class CouponQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Coupon(models.Model):
    """A marketing-managed discount code — order-wide or tied to one product.

    Deactivating (retiring) or deleting a coupon never touches past orders:
    ``Order.coupon_code``/``discount_amount`` are snapshotted at checkout,
    the same denormalization principle as ``OrderItem``.
    """

    code = models.CharField(max_length=20, unique=True, validators=[code_validator])
    percent_off = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    product = models.ForeignKey(
        Product,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="coupons",
        help_text="Leave blank for an order-wide discount.",
    )
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CouponQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.upper()
        super().save(*args, **kwargs)

    def is_expired(self):
        return bool(self.expires_at and self.expires_at <= timezone.now())

    def is_usable(self):
        return self.is_active and not self.is_expired()

    @property
    def scope_display(self):
        return self.product.name if self.product_id else "Order-wide"
