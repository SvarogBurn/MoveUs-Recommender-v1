import datetime

from shared.errors.mu_error import MUError, MUErrorCode


def validate_preferred_event_duration(duration: int = None):
    if duration and not 1 <= duration <= 200:
        raise MUError(MUErrorCode.PREFERRED_EVENT_DURATION_RANGE)


def validate_max_travel_distance(distance: int = None):
    if distance is not None and not 1 <= distance < 2e5:
        raise MUError(MUErrorCode.TRAVEL_DISTANCE_RANGE)


def validate_profile(
    first_name: str = None,
    last_name: str = None,
    date_of_birth: datetime.date = None,
    bio: str = None,
):

    if first_name:
        if len(first_name) > 32:
            raise MUError(MUErrorCode.FIRSTNAME_MAX_LENGTH)
        if len(first_name) < 2:
            raise MUError(MUErrorCode.FIRSTNAME_MIN_LENGTH)

    if last_name:
        if len(last_name) > 32:
            raise MUError(MUErrorCode.LASTNAME_MAX_LENGTH)
        if len(last_name) < 2:
            raise MUError(MUErrorCode.LASTNAME_MIN_LENGTH)

    if date_of_birth:
        age = (datetime.date.today() - date_of_birth).days / 365
        if age < 18:
            raise MUError(MUErrorCode.USER_MIN_AGE)
        if age > 100:
            raise MUError(MUErrorCode.USER_MAX_AGE)

    if bio and len(bio) > 512:
        raise MUError(MUErrorCode.BIO_MAX_LENGTH)
