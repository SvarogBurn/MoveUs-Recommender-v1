import re

from allauth.utils import valid_email_or_none

from main.user.models import User
from shared.errors.mu_error import MUError, MUErrorCode


def validate_sign_up(username: str, email: str, password: str):
    if len(password) < 8:
        raise MUError(MUErrorCode.PASSWORD_MIN_LENGTH)

    if not re.search(r"[A-Za-z]", password):
        raise MUError(MUErrorCode.PASSWORD_MISSING_LETTER)

    if not re.search(r"[0-9]", password):
        raise MUError(MUErrorCode.PASSWORD_MISSING_NUMBER)

    if not re.search(r"[^a-zA-Z0-9]", password):
        raise MUError(MUErrorCode.PASSWORD_MISSING_SPECIAL)

    if len(username) < 3:
        raise MUError(MUErrorCode.USERNAME_MIN_LENGTH)

    if len(username) > 32:
        raise MUError(MUErrorCode.USERNAME_MAX_LENGTH)

    if not re.match(r"^[0-9A-Za-z_]*$", username):
        raise MUError(MUErrorCode.USERNAME_ALLOWED_CHARACTERS)

    if User.objects.filter(username__iexact=username).exists():
        raise MUError(MUErrorCode.USERNAME_ALREADY_TAKEN)

    if not valid_email_or_none(email):
        raise MUError(MUErrorCode.EMAIL_INVALID)

    if User.objects.filter(email__iexact=email).exists():
        raise MUError(MUErrorCode.EMAIL_ALREADY_TAKEN)