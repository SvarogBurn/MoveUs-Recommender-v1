from datetime import datetime

from django.utils.timezone import now as tz_now

from shared.enums import Gender
from shared.errors.mu_error import MUError, MUErrorCode


def validate_location_requirements(
    location_id: int = None,
    location_longitude: float = None,
    location_latitude: float = None,
) -> None:
    if not location_id and not (location_longitude and location_latitude):
        raise MUError(MUErrorCode.MINIMAL_LOCATION_REQUIREMENTS_MISSING)


def validate_event(
    title: str = None,
    description: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    max_participants: int = None,
    min_age: int = None,
    max_age: int = None,
    accepted_genders: list = None,
):

    if title and len(title) < 4:
        raise MUError(MUErrorCode.EVENT_TITLE_MIN_LENGTH)

    if title and len(title) > 256:
        raise MUError(MUErrorCode.EVENT_TITLE_MAX_LENGTH)

    if description and len(description) > 131072:
        raise MUError(MUErrorCode.EVENT_DESCRIPTION_MAX_LENGTH)

    now = tz_now()

    if start_time and start_time < now:
        raise MUError(MUErrorCode.EVENT_START_TIME_INVALID)

    if end_time and end_time < now:
        raise MUError(MUErrorCode.EVENT_END_TIME_INVALID)

    if start_time and end_time and end_time < start_time:
        raise MUError(MUErrorCode.EVENT_TIMES_RELATION_INVALID)

    if max_participants and max_participants < 1:
        raise MUError(MUErrorCode.EVENT_MIN_MAX_PARTICIPANTS)

    if min_age and not 18 <= min_age <= 100:
        raise MUError(MUErrorCode.EVENT_MIN_AGE)

    if max_age and not 18 <= max_age <= 100:
        raise MUError(MUErrorCode.EVENT_MAX_AGE)

    if min_age and max_age and min_age >= max_age:
        raise MUError(MUErrorCode.EVENT_MIN_MAX_AGE)

    if accepted_genders and Gender.PREFER_NOT_TO_SAY in accepted_genders:
        raise MUError(MUErrorCode.EVENT_ACCEPTED_GENDERS)
