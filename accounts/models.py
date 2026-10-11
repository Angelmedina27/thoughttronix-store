from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


def normalize_email(email: str | None) -> str:
    """Trim and lowercase, so stored emails agree with the case-insensitive
    uniqueness rule."""
    return (email or "").strip().lower()


class UserManager(DjangoUserManager):
    def email_in_use(self, email: str, exclude_pk: int | None = None) -> bool:
        """Whether another account already holds ``email``, ignoring case.

        Blank emails are never "in use" — grandfathered accounts may share
        them. ``exclude_pk`` lets a user keep their own address.
        """
        email = normalize_email(email)
        if not email:
            return False
        return self.filter(email__iexact=email).exclude(pk=exclude_pk).exists()


class User(AbstractUser):
    """The store's user model.

    Roles use Django's own vocabulary and nothing else: customers are
    plain users, employees are ``is_staff``, the admin is ``is_superuser``.
    """

    # Nullable per the PRD: an absent job title is unknown, not empty.
    job_title = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001
    # Null means "never changed since signup" — unknown, not empty.
    password_changed_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        constraints = [
            # Case-insensitive uniqueness for real emails only: accounts
            # created before email was collected keep their blank value.
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(email=""),
                name="accounts_user_email_ci_unique",
                violation_error_message="An account with this email already exists.",
            ),
        ]

    def save(self, *args, **kwargs):
        self.email = normalize_email(self.email)
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        """Stamp ``password_changed_at`` — but only for existing users, so
        account creation does not count as a change. Every Django password
        path (change, reset, admin, ``createsuperuser``) runs through here.
        """
        super().set_password(raw_password)
        if self.pk is not None:
            self.password_changed_at = timezone.now()
