from datetime import datetime

from django.utils.timezone import now as tz_now

from main.event.models import Event, EventMember
from main.user.models import User
from shared.enums import EventPhase, Gender, MemberRole
from shared.errors.mu_error import MUError, MUErrorCode


def validate_event_not_started(event: Event):
    if event.start_time <= tz_now():
        raise MUError(MUErrorCode.EVENT_ALREADY_STARTED)


def validate_event_not_ended(event: Event):
    if event.end_time <= tz_now():
        raise MUError(MUErrorCode.EVENT_ALREADY_ENDED)


def validate_join_eligibility(event: Event, user: User):
    validate_event_not_started(event)
    if (
        event.max_participants is not None
        and event.participant_count() >= event.max_participants
    ):
        raise MUError(MUErrorCode.EVENT_FULL)
    if (
        event.accepted_genders is not None
        and user.gender not in event.accepted_genders
    ):
        raise MUError(MUErrorCode.GENDER_NOT_ALLOWED)
    if event.min_age and (not user.date_of_birth or user.age < event.min_age):
        raise MUError(MUErrorCode.AGE_RANGE_INVALID)
    if event.max_age and (not user.date_of_birth or user.age > event.max_age):
        raise MUError(MUErrorCode.AGE_RANGE_INVALID)


def validate_finish_eligibility(event: Event):
    if tz_now() < event.end_time:
        raise MUError(MUErrorCode.CANNOT_FINISH_BEFORE_END)


def validate_alter_max_participants(max_participants: int, current_count: int):
    if max_participants and max_participants < current_count:
        raise MUError(MUErrorCode.EVENT_MIN_MAX_PARTICIPANTS)


def validate_spectate_eligibility(member: EventMember):
    if member.role != MemberRole.PARTICIPANT:
        raise MUError(MUErrorCode.CANNOT_DEMOTE_YOURSELF)


def validate_leave_eligibility(member: EventMember):
    if member.role == MemberRole.ORGANIZER:
        raise MUError(MUErrorCode.CANNOT_LEAVE_AS_ORGANIZATOR)


def validate_kick_eligibility(
    requesting_user_id: int,
    target_user_id: int,
    event: Event,
    target_member: EventMember = None
):
    if requesting_user_id == target_user_id:
        raise MUError(MUErrorCode.CANNOT_KICK_YOURSELF)
    validate_event_not_ended(event)
    if target_member is not None and target_member.role == MemberRole.ORGANIZER:
        raise MUError(MUErrorCode.CANNOT_KICK_ORGANIZER)


def validate_confirm_participation(requesting_member: EventMember, target_member: EventMember):
    if requesting_member.role < MemberRole.MODERATOR:
        raise MUError(MUErrorCode.NOT_MODERATOR)
    if target_member.role != MemberRole.PARTICIPANT:
        raise MUError(MUErrorCode.CANNOT_CONFIRM_NON_PARTICIPATING_MEMBER)


def validate_rate_eligibility(event: Event, member: EventMember):
    if event.phase != EventPhase.FINISHED:
        raise MUError(MUErrorCode.CANNOT_RATE_UNFINISHED_EVENT)
    if member.role == MemberRole.ORGANIZER:
        raise MUError(MUErrorCode.CANNOT_RATE_OWN_EVENT)
    if not member.has_participated:
        raise MUError(MUErrorCode.CANNOT_RATE_NO_PARTICIPATION)


def validate_like_eligibility(
    event: Event,
    member: EventMember,
    user_id: int,
    target_user_id: int
):
    if user_id == target_user_id:
        raise MUError(MUErrorCode.CANNOT_LIKE_YOURSELF)
    if event.phase != EventPhase.FINISHED:
        raise MUError(MUErrorCode.CANNOT_LIKE_BEFORE_FINISH)
    if not member.has_participated:
        raise MUError(MUErrorCode.CANNOT_LIKE_DIDNT_PARTICIPATE)


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
