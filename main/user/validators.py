import datetime

from shared.errors.mu_error import MUError, MUErrorCode


def validate_preferred_event_duration(duration: int = None):
    if duration and not 1 <= duration <= 200:
        raise MUError(MUErrorCode.PREFERRED_EVENT_DURATION_RANGE)


def validate_max_travel_distance(distance: int = None):
    if distance is not None and not 1 <= distance < 2e5:
        raise MUError(MUErrorCode.TRAVEL_DISTANCE_RANGE)


def validate_likert(value: int = None):
    """Survey scale answers (Q4, Q9, Q14, Q15, Q17, Q18, Q19)."""
    if value is not None and not 1 <= value <= 5:
        raise MUError(MUErrorCode.LIKERT_RANGE)


def validate_weekly_activity_target(value: int = None):
    if value is not None and not 1 <= value <= 7:
        raise MUError(MUErrorCode.WEEKLY_ACTIVITY_TARGET_RANGE)


def validate_preferred_group_size(value: int = None):
    if value is not None and not 1 <= value <= 10:
        raise MUError(MUErrorCode.PREFERRED_GROUP_SIZE_RANGE)


# scalar preference fields that carry a 1-5 Likert answer
LIKERT_PREFERENCE_FIELDS = (
    "leadership_inclination",
    "pushes_through_discomfort",
    "enjoys_meeting_new_people",
    "activity_vs_social",
    "motivated_by_competition",
    "planning_horizon",
    "feels_like_burden",
)


def validate_preferences(fields: dict):
    validate_preferred_event_duration(fields.get("preferred_session_duration"))
    validate_max_travel_distance(fields.get("max_travel_distance"))
    validate_weekly_activity_target(fields.get("weekly_activity_target"))
    validate_preferred_group_size(fields.get("preferred_group_size"))
    for name in LIKERT_PREFERENCE_FIELDS:
        validate_likert(fields.get(name))


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
