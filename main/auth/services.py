from typing import Any

from allauth.account import app_settings as allauth_settings
from allauth.account.adapter import get_adapter
from allauth.account.forms import ResetPasswordForm
from allauth.account.models import EmailAddress
from allauth.account.utils import (
    complete_signup,
    perform_login,
    send_email_confirmation,
)
from django.contrib.auth import authenticate
from django.contrib.auth import logout as django_logout
from django.contrib.auth.models import AbstractUser

from main.auth.validators import validate_sign_up
from main.user.models import User
from main.user.services import UserService
from shared.errors.mu_error import MUError, MUErrorCode

SESSION_LIFETIME_SHORT = 60 * 60 * 24          # 1 day
SESSION_LIFETIME_LONG = 60 * 60 * 24 * 90      # 90 days


class AuthService:

    @staticmethod
    def login(
        request: Any,
        user: str,
        password: str,
        remember_me: bool = False,
    ) -> AbstractUser:
        is_email = "@" in user

        profile = None
        if is_email:
            profile = authenticate(request, email=user, password=password)
        else:
            profile = authenticate(request, username=user.lower(), password=password)

        if profile is None:
            raise MUError(MUErrorCode.INVALID_LOGIN)

        perform_login(request, profile)
        request.session.set_expiry(
            SESSION_LIFETIME_LONG if remember_me else SESSION_LIFETIME_SHORT
        )

        return profile

    @staticmethod
    def logout(request: Any) -> None:
        django_logout(request)

    @staticmethod
    def sign_up(
        request: Any,
        email: str,
        username: str,
        password: str,
        remember_me: bool = False,
    ) -> AbstractUser:
        validate_sign_up(username, email, password)

        user = get_adapter(request).new_user(request)
        user.username = username
        user.email = email
        user.set_password(password)
        user.save()

        UserService.initialize_privacy_settings(user.id)

        if (
            allauth_settings.EMAIL_VERIFICATION
            == allauth_settings.EmailVerificationMethod.MANDATORY
        ):
            EmailAddress.objects.create(
                user=user, email=email, primary=True, verified=False
            )
        else:
            EmailAddress.objects.create(
                user=user, email=email, primary=True, verified=True
            )

        complete_signup(request, user, allauth_settings.EMAIL_VERIFICATION, None)
        perform_login(request, user, allauth_settings.EMAIL_VERIFICATION)
        request.session.set_expiry(
            SESSION_LIFETIME_LONG if remember_me else SESSION_LIFETIME_SHORT
        )

        return user

    @staticmethod
    def delete_account(request: Any) -> None:
        user: User = request.user
        if not user.id:
            raise MUError(MUErrorCode.AUTHENTICATION_ERROR)
        AuthService.logout(request)
        user.delete()

    @staticmethod
    def send_confirmation_email(request: Any) -> None:
        send_email_confirmation(request, request.user)

    @staticmethod
    def send_password_reset_email(request: Any) -> ResetPasswordForm:
        email = request.user.email
        form = ResetPasswordForm(data={"email": email})
        if form.is_valid():
            form.save(request=None)
        return form

    @staticmethod
    def is_username_taken(username: str) -> bool:
        return User.objects.filter(username=username.lower()).exists()

    @staticmethod
    def is_email_taken(email: str) -> bool:
        return User.objects.filter(email=email).exists()

    @staticmethod
    def is_logged_in(request: Any) -> bool:
        return bool(request.user)
