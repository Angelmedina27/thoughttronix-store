from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.timesince import timeuntil
from django.views.generic import CreateView, FormView, TemplateView

from . import security
from .forms import (
    EmailChangeForm,
    SignInForm,
    SignupForm,
    StyledPasswordChangeForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
)


class SignupView(SuccessMessageMixin, CreateView):
    """Create a customer account, then hand off to the login page.

    New users sign in themselves — auto-login after signup is left as a
    student exercise.
    """

    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:login")
    success_message = "Account created — you can now sign in."


class SignInView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = SignInForm


class SignOutView(LogoutView):
    def post(self, request, *args, **kwargs):
        # Flash after super() has flushed the session, or the message
        # would be wiped along with it.
        response = super().post(request, *args, **kwargs)
        messages.info(request, "You have signed out.")
        return response


class SecurityCenterView(LoginRequiredMixin, TemplateView):
    """The Security Center hub: the signed-in user's account at a glance.

    Open to every role; the template reads everything it needs off
    ``user``, so the view adds nothing to the context.
    """

    template_name = "accounts/security.html"


class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    """Change the password from the Security Center.

    Django's view does the security-critical part: it keeps this session
    signed in and, because the password hash changed, every other session
    is signed out. This view adds the alert and the trip back to the hub.
    """

    form_class = StyledPasswordChangeForm
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:security")
    success_message = "Your password has been changed."

    def form_valid(self, form):
        response = super().form_valid(form)
        security.send_password_changed_alert(self.request.user, self.request)
        return response


class ChangeEmailView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    """Add or change the account's email from the Security Center.

    The change takes effect immediately; the alert goes to the *previous*
    address, so the real owner hears about it even if the new address
    isn't theirs.
    """

    form_class = EmailChangeForm
    template_name = "accounts/email_change.html"
    success_url = reverse_lazy("accounts:security")
    success_message = "Your email has been updated."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        old_email = self.request.user.email
        user = form.save()
        security.send_email_changed_alert(user, old_email, self.request)
        return super().form_valid(form)


def _reset_link_lifetime() -> str:
    """``PASSWORD_RESET_TIMEOUT`` in words — "1 hour" by default."""
    now = timezone.now()
    lifetime = timeuntil(now + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT), now)
    # timeuntil joins with non-breaking spaces; the plain-text email wants
    # ordinary ones.
    return lifetime.replace(" ", " ")


class RequestPasswordResetView(PasswordResetView):
    """Step one of the forgot-password loop: ask for the account's email.

    Every submission lands on the same "check your inbox" page, whether or
    not the email has an account — the form never reveals who shops here.
    """

    form_class = StyledPasswordResetForm
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/email/password_reset.txt"
    subject_template_name = "accounts/email/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")

    def form_valid(self, form):
        self.extra_email_context = {"link_lifetime": _reset_link_lifetime()}
        return super().form_valid(form)


class PasswordResetSentView(PasswordResetDoneView):
    """Step two: the generic "if an account exists…" page."""

    template_name = "accounts/password_reset_done.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(link_lifetime=_reset_link_lifetime(), **kwargs)


class ChooseNewPasswordView(SuccessMessageMixin, PasswordResetConfirmView):
    """Step three: the link from the email, where a new password is chosen.

    Django's view checks the token — expired, tampered and already-used
    links all render the invalid-link state. Setting the password changes
    its hash, which signs out every session. The user is sent to sign in
    with the new password rather than signed in automatically, matching
    how signup hands off.
    """

    form_class = StyledSetPasswordForm
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:login")
    success_message = "Your password has been reset — sign in with your new password."

    def form_valid(self, form):
        response = super().form_valid(form)
        security.send_password_reset_alert(form.user, self.request)
        return response
