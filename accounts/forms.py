from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from . import security
from .models import User, normalize_email


class SignupForm(UserCreationForm):
    """Django's stock signup fields — username, password and confirmation —
    plus a required email, so the account can be recovered later.

    The widgets carry DaisyUI classes because plain Django forms own their
    own styling here.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def clean_email(self):
        # A friendly message up front; the database constraint is still
        # the real guarantee.
        email = normalize_email(self.cleaned_data["email"])
        if User.objects.email_in_use(email):
            raise forms.ValidationError("An account with this email already exists.")
        return email


class LoginThrottleMixin:
    """Lock out a username + network address after repeated failed sign-ins.

    Mix in ahead of an ``AuthenticationForm``; the login views already pass
    the form its ``request``. A locked-out pair is turned away before the
    password is even checked, so a correct guess during the lockout teaches
    an attacker nothing. A successful sign-in clears the count.
    """

    def clean(self):
        username = self.cleaned_data.get("username")
        if username is None:
            return super().clean()
        ip = self._client_ip()
        if not security.login_allowed(username, ip):
            raise forms.ValidationError(security.LOCKOUT_MESSAGE, code="locked_out")
        try:
            cleaned_data = super().clean()
        except forms.ValidationError:
            security.record_login_failure(username, ip)
            raise
        security.clear_login_failures(username, ip)
        return cleaned_data

    def _client_ip(self) -> str:
        if self.request is None:
            return "unknown"
        return self.request.META.get("REMOTE_ADDR") or "unknown"


class SignInForm(LoginThrottleMixin, AuthenticationForm):
    """The stock authentication form, throttled and dressed in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class AdminSignInForm(LoginThrottleMixin, AdminAuthenticationForm):
    """The Django admin's sign-in form — which still turns away non-staff —
    under the same lockout as the storefront."""


class StyledPasswordChangeForm(PasswordChangeForm):
    """Django's stock password-change form — current password, new password
    twice, the configured validators — dressed in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class StyledPasswordResetForm(PasswordResetForm):
    """Django's stock reset-request form, rate-limited and dressed in DaisyUI.

    The stock form already does the security-critical part: it matches the
    email case-insensitively, mails only active accounts with a usable
    password, and behaves identically whether or not an account exists.
    Emails over the per-address limit are skipped silently, so a throttled
    request looks exactly like any other.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        if security.allow_reset_email(to_email):
            super().send_mail(
                subject_template_name,
                email_template_name,
                context,
                from_email,
                to_email,
                html_email_template_name=html_email_template_name,
            )


class StyledSetPasswordForm(SetPasswordForm):
    """Django's stock choose-a-new-password form — new password twice, the
    same validators as signup — dressed in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class EmailChangeForm(forms.Form):
    """Add or change the signed-in user's email, proven by their current
    password.

    The new address is held to the signup uniqueness rule, except that a
    user may re-enter their own address.
    """

    email = forms.EmailField(label="New email")
    current_password = forms.CharField(
        label="Current password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs["autocomplete"] = "email"
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def clean_email(self):
        email = normalize_email(self.cleaned_data["email"])
        if User.objects.email_in_use(email, exclude_pk=self.user.pk):
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_current_password(self):
        password = self.cleaned_data["current_password"]
        if not self.user.check_password(password):
            raise forms.ValidationError(
                "Your current password was entered incorrectly."
            )
        return password

    def save(self) -> User:
        self.user.email = self.cleaned_data["email"]
        self.user.save(update_fields=["email"])
        return self.user
