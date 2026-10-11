from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)

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


class SignInForm(AuthenticationForm):
    """The stock authentication form, dressed in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class StyledPasswordChangeForm(PasswordChangeForm):
    """Django's stock password-change form — current password, new password
    twice, the configured validators — dressed in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"
