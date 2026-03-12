import datetime
from typing import Any

from django.utils.timezone import now

from main.event.models import Event, EventMember
from main.location.models import Location
from main.user.models import User
from shared.enums import MemberRole, SkillLevel
from shared.errors.mu_error import MUError, MUErrorCode
from main.chat.services import ChatService


def _get_event_error_code(role: MemberRole) -> MUErrorCode:
    match role:
        case MemberRole.ORGANIZER:
            return MUErrorCode.NOT_ORGANIZER
        case MemberRole.MODERATOR:
            return MUErrorCode.NOT_MODERATOR
        case MemberRole.PARTICIPANT:
            return MUErrorCode.NOT_PARTICIPANT
    return MUErrorCode.NOT_MEMBER


class EventService:
    @staticmethod
    def create_event(
        user: User,
        title: str,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        location: Location,
        activity_id: int,
        skill_level: SkillLevel,
        **kwargs: Any,
    ) -> Event:
        event = Event.objects.create(
            title=title,
            start_time=start_time,
            end_time=end_time,
            location=location,
            activity_id=activity_id,
            skill_level=skill_level,
            **kwargs,
        )
        EventMember.objects.create(
            event=event, user=user, role=MemberRole.ORGANIZER, has_participated=True
        )

        ChatService.create_chat_for_event(event)
        return event

    @staticmethod
    def get_event(
        event_id: int,
        user_id: int | None = None,
        minimal_role: MemberRole | None = None,
    ) -> Event:
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            raise MUError(MUErrorCode.EVENT_DOES_NOT_EXIST)

        if minimal_role is not None:
            if user_id is None:
                raise MUError(_get_event_error_code(minimal_role))

            role_error_code = _get_event_error_code(minimal_role)

            try:
                em = EventMember.objects.get(pk=(user_id, event.id))
                if em.role < minimal_role:
                    raise MUError(role_error_code)
            except EventMember.DoesNotExist:
                raise MUError(role_error_code)

        return event

    @staticmethod
    def get_event_with_member(
        event_id: int,
        user_id: int,
        minimal_role: MemberRole | None = None,
    ) -> tuple[Event, EventMember]:
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            raise MUError(MUErrorCode.EVENT_DOES_NOT_EXIST)

        try:
            em = EventMember.objects.get(pk=(user_id, event.id))
            if minimal_role is None or em.role >= minimal_role:
                return event, em
        except EventMember.DoesNotExist:
            pass

        raise MUError(_get_event_error_code(minimal_role))

    @staticmethod
    def alter_event(event: Event, **fields: Any) -> Event:
        for field, value in fields.items():
            if value is not None:
                setattr(event, field, value)
        event.save()
        return event

    @staticmethod
    def join_event(event: Event, user: User) -> EventMember:
        if event.start_time <= now():
            raise MUError(MUErrorCode.EVENT_ALREADY_STARTED)

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

        try:
            member = EventMember.objects.get(pk=(user.id, event.id))
            if member.role != MemberRole.SPECTATOR:
                raise MUError(MUErrorCode.ALREADY_IN_EVENT)
            member.role = MemberRole.PARTICIPANT
            member.save()
        except EventMember.DoesNotExist:
            member = EventMember.objects.create(
                user_id=user.id, event_id=event.id, role=MemberRole.PARTICIPANT
            )

        return member

    @staticmethod
    def finish_event(event_id: int, user_id: int) -> Event:
        event = EventService.get_event(event_id, user_id, MemberRole.ORGANIZER)

        if now() < event.end_time:
            raise MUError(MUErrorCode.CANNOT_FINISH_BEFORE_END)

        if (
            EventMember.objects.filter(
                event_id=event_id, participates=True, has_participated__isnull=True
            ).count()
            != 0
        ):
            raise MUError(MUErrorCode.CANNOT_FINISH_WITH_UNCONFIRMED)

        event.finished = True
        event.save()

        from main.notification.services import NotificationService

        NotificationService.send_event_finished(event_id)

        return event

    @staticmethod
    def delete_event(event: Event) -> None:
        from main.location.services import LocationService

        LocationService.release(event.location)
        event.delete()
