import datetime
from typing import Any

from django.db.models import Prefetch, QuerySet
from django.utils.timezone import now

from main.event.models import Event, EventMember, EventMemberLike, EventReport
from main.event.validators import validate_event, validate_location_requirements
from main.location.models import Location
from main.location.validators import validate_location
from main.user.models import User
from shared.enums import MemberRole, SkillLevel
from shared.errors.mu_error import MUError, MUErrorCode
from shared.storage import storage_backend


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
    def _queryset() -> QuerySet[Event]:
        return Event.objects.select_related("location", "activity").prefetch_related(
            Prefetch(
                "members",
                queryset=EventMember.objects.select_related("user"),
                to_attr="_members",
            )
        )

    @staticmethod
    def get_event_by_id(event_id: int) -> Event:
        try:
            return EventService._queryset().get(pk=event_id)
        except Event.DoesNotExist:
            raise MUError(MUErrorCode.EVENT_DOES_NOT_EXIST)

    @staticmethod
    def get_anonymous_events() -> QuerySet[Event]:
        return EventService._queryset().all()[:6]

    @staticmethod
    def get_recommended_events() -> QuerySet[Event]:
        return EventService._queryset().all()

    @staticmethod
    def get_joined_events(user_id: int) -> QuerySet[Event]:
        return EventService._queryset().filter(
            id__in=EventMember.objects.filter(user_id=user_id)
            .exclude(role=MemberRole.ORGANIZER)
            .values("event_id")
        )

    @staticmethod
    def get_owned_events(user_id: int) -> QuerySet[Event]:
        return EventService._queryset().filter(
            id__in=EventMember.objects.filter(
                user_id=user_id, role=MemberRole.ORGANIZER
            ).values("event_id")
        )

    @staticmethod
    def get_past_joined_events(user_id: int) -> QuerySet[Event]:
        return EventService._queryset().filter(
            end_time__lte=now(),
            id__in=EventMember.objects.filter(user_id=user_id)
            .exclude(role=MemberRole.ORGANIZER)
            .values("event_id"),
        )

    @staticmethod
    def get_ongoing_joined_events(user_id: int) -> QuerySet[Event]:
        time = now()
        return EventService._queryset().filter(
            start_time__lt=time,
            end_time__gt=time,
            id__in=EventMember.objects.filter(user_id=user_id)
            .exclude(role=MemberRole.ORGANIZER)
            .values("event_id"),
        )

    @staticmethod
    def get_future_joined_events(user_id: int) -> QuerySet[Event]:
        return EventService._queryset().filter(
            start_time__gte=now(),
            id__in=EventMember.objects.filter(user_id=user_id)
            .exclude(role=MemberRole.ORGANIZER)
            .values("event_id"),
        )

    @staticmethod
    def get_unrated_events(user_id: int) -> QuerySet[Event]:
        return EventService._queryset().filter(
            finished=True,
            id__in=EventMember.objects.filter(
                user_id=user_id, score__isnull=True, has_participated=True
            )
            .exclude(role=MemberRole.ORGANIZER)
            .values("event_id"),
        )

    @staticmethod
    def get_unfinished_events(user_id: int) -> QuerySet[Event]:
        return EventService._queryset().filter(
            finished=False,
            id__in=EventMember.objects.filter(
                user_id=user_id, role__in=(MemberRole.ORGANIZER, MemberRole.MODERATOR)
            ).values("event_id"),
        )

    @staticmethod
    def create_event(
        user: User,
        title: str,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        location_id: int | None,
        location_longitude: float | None,
        location_latitude: float | None,
        location_address_line1: str | None,
        location_address_line2: str | None,
        location_zip_code: int | None,
        location_country_code=None,
        location_region: str | None = None,
        location_name: str | None = None,
        activity_id: int = None,
        skill_level: SkillLevel = None,
        **kwargs: Any,
    ) -> Event:
        validate_location_requirements(location_id, location_longitude, location_latitude)
        validate_location(
            location_longitude,
            location_latitude,
            location_address_line1,
            location_address_line2,
            location_zip_code,
            location_region,
            location_name,
        )
        validate_event(
            title,
            kwargs.get("description"),
            start_time,
            end_time,
            kwargs.get("max_participants"),
            kwargs.get("min_age"),
            kwargs.get("max_age"),
            kwargs.get("accepted_genders"),
        )

        from main.location.services import LocationService

        location = LocationService.get_or_create(
            location_id=location_id,
            longitude=location_longitude,
            latitude=location_latitude,
            address_line_1=location_address_line1,
            address_line_2=location_address_line2,
            zip_code=location_zip_code,
            country_code=location_country_code,
            region=location_region,
            name=location_name,
        )

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
        validate_event(
            fields.get("title"),
            fields.get("description"),
            fields.get("start_time"),
            fields.get("end_time"),
            fields.get("max_participants"),
        )
        max_participants = fields.get("max_participants")
        if max_participants and max_participants < event.participant_count():
            raise MUError(MUErrorCode.EVENT_MIN_MAX_PARTICIPANTS)

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

    @staticmethod
    def spectate_event(event: Event, user: User) -> EventMember:
        if event.start_time <= now():
            raise MUError(MUErrorCode.EVENT_ALREADY_STARTED)

        try:
            member = EventMember.objects.get(pk=(user.id, event.id))
            if member.role != MemberRole.PARTICIPANT:
                raise MUError(MUErrorCode.CANNOT_DEMOTE_YOURSELF)
            member.role = MemberRole.SPECTATOR
            member.save()
        except EventMember.DoesNotExist:
            member = EventMember.objects.create(
                user_id=user.id, event_id=event.id, role=MemberRole.SPECTATOR
            )

        return member

    @staticmethod
    def leave_event(event: Event, user: User) -> None:
        if event.end_time <= now():
            raise MUError(MUErrorCode.EVENT_ALREADY_ENDED)

        try:
            member = EventMember.objects.get(pk=(user.id, event.id))
            if member.role == MemberRole.ORGANIZER:
                raise MUError(MUErrorCode.CANNOT_LEAVE_AS_ORGANIZATOR)
            member.delete()
        except EventMember.DoesNotExist:
            raise MUError(MUErrorCode.NOT_MEMBER)

    @staticmethod
    def kick_member(
        event: Event, requesting_user_id: int, target_user_id: int
    ) -> None:
        if requesting_user_id == target_user_id:
            raise MUError(MUErrorCode.CANNOT_KICK_YOURSELF)

        if event.end_time <= now():
            raise MUError(MUErrorCode.EVENT_ALREADY_ENDED)

        try:
            member = EventMember.objects.get(pk=(target_user_id, event.id))
            if member.role == MemberRole.ORGANIZER:
                raise MUError(MUErrorCode.CANNOT_KICK_ORGANIZER)
            member.delete()
        except EventMember.DoesNotExist:
            raise MUError(MUErrorCode.EVENT_MEMBER_DOES_NOT_EXIST)

    @staticmethod
    def confirm_participation(
        target_user_id: int,
        event_id: int,
        participated: bool,
        requesting_user_id: int,
    ) -> None:
        try:
            requesting_member = EventMember.objects.get(
                pk=(requesting_user_id, event_id)
            )
            if requesting_member.role < MemberRole.MODERATOR:
                raise MUError(MUErrorCode.NOT_MODERATOR)
        except EventMember.DoesNotExist:
            raise MUError(MUErrorCode.NOT_MODERATOR)

        try:
            member = EventMember.objects.get(pk=(target_user_id, event_id))
            if member.role == MemberRole.PARTICIPANT:
                member.has_participated = participated
                member.save()
                return
        except EventMember.DoesNotExist:
            pass

        raise MUError(MUErrorCode.CANNOT_CONFIRM_NON_PARTICIPATING_MEMBER)

    @staticmethod
    def rate_event(
        event: Event, member: EventMember, score, comment: str = None
    ) -> None:
        if comment and len(comment) > 512:
            raise MUError(MUErrorCode.RATE_COMMENT_MAX_LENGTH)

        if not event.finished:
            raise MUError(MUErrorCode.CANNOT_RATE_UNFINISHED_EVENT)

        if member.role == MemberRole.ORGANIZER:
            raise MUError(MUErrorCode.CANNOT_RATE_OWN_EVENT)

        if not member.has_participated:
            raise MUError(MUErrorCode.CANNOT_RATE_NO_PARTICIPATION)

        member.score = score
        if comment:
            member.comment = comment
        member.save()

    @staticmethod
    def like_member(
        event: Event,
        member: EventMember,
        user_id: int,
        target_user_id: int,
        like: bool,
    ) -> None:
        if user_id == target_user_id:
            raise MUError(MUErrorCode.CANNOT_LIKE_YOURSELF)

        if not event.finished:
            raise MUError(MUErrorCode.CANNOT_LIKE_BEFORE_FINISH)

        if not member.has_participated:
            raise MUError(MUErrorCode.CANNOT_LIKE_DIDNT_PARTICIPATE)

        try:
            other = EventMember.objects.get(pk=(target_user_id, event.id))
            if other.participates and other.has_participated:
                try:
                    eml = EventMemberLike.objects.get(
                        pk=(event.id, user_id, target_user_id)
                    )
                    eml.like = like
                    eml.save()
                except EventMemberLike.DoesNotExist:
                    EventMemberLike.objects.create(
                        user_1_id=user_id,
                        user_2_id=target_user_id,
                        event_id=event.id,
                        like=like,
                    )
                return
        except EventMember.DoesNotExist:
            pass

        raise MUError(MUErrorCode.CANNOT_LIKE_NOT_PARTICIPANT)

    @staticmethod
    def get_organizer(
        event_id: int, _members: list | None = None
    ) -> EventMember | None:
        if _members is not None:
            result = [m for m in _members if m.role == MemberRole.ORGANIZER]
            return result[0] if result else None
        return EventMember.objects.filter(
            event_id=event_id, role=MemberRole.ORGANIZER
        ).first()

    @staticmethod
    def get_members_by_role(
        event_id: int, role: MemberRole, _members: list | None = None
    ):
        if _members is not None:
            return [m for m in _members if m.role == role]
        return EventMember.objects.filter(event_id=event_id, role=role)

    @staticmethod
    def get_member_count(event_id: int, _members: list | None = None) -> int:
        if _members is not None:
            return len(_members)
        return EventMember.objects.filter(event_id=event_id).count()

    @staticmethod
    def get_user_role(
        event_id: int, user_id: int, _members: list | None = None
    ) -> int | None:
        if not user_id:
            return None
        if _members is not None:
            result = [m for m in _members if m.user_id == user_id]
            return result[0].role if result else None
        try:
            return EventMember.objects.get(pk=(user_id, event_id)).role
        except EventMember.DoesNotExist:
            return None

    @staticmethod
    def get_average_score(
        event_id: int, _members: list | None = None
    ) -> float | None:
        if _members is not None:
            scores = [m.score for m in _members if m.score is not None]
            return (sum(scores) / len(scores) + 1) if scores else None
        from django.db.models import Avg

        score = EventMember.objects.filter(event_id=event_id).aggregate(
            Avg("score")
        )["score__avg"]
        return score + 1 if score is not None else None

    @staticmethod
    def get_reviews(event_id: int, _members: list | None = None) -> list:
        if _members is not None:
            return [m for m in _members if m.comment is not None]
        return list(
            EventMember.objects.filter(event_id=event_id, comment__isnull=False)
        )

    @staticmethod
    def get_unconfirmed_participants(event_id: int):
        return EventMember.objects.filter(
            event_id=event_id, participates=True, has_participated__isnull=True
        )

    @staticmethod
    def get_organizing_events(user_id: int) -> QuerySet[Event]:
        return Event.objects.filter(
            id__in=EventMember.objects.filter(
                user_id=user_id, role=MemberRole.ORGANIZER
            ).values("event_id")
        )

    @staticmethod
    def get_attending_events(user_id: int) -> QuerySet[Event]:
        return Event.objects.filter(
            id__in=EventMember.objects.filter(
                user_id=user_id,
                role__in=[
                    MemberRole.PARTICIPANT,
                    MemberRole.MODERATOR,
                    MemberRole.SPECTATOR,
                ],
            ).values("event_id")
        )

    @staticmethod
    def report_event(
        reporter_id: int, event_id: int, comment: str = None
    ) -> None:
        if comment and len(comment) > 512:
            raise MUError(MUErrorCode.REPORT_COMMENT_MAX_LENGTH)

        try:
            Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)

        EventReport.objects.create(
            reporter_id=reporter_id, reported_id=event_id, comment=comment
        )

    @staticmethod
    def get_event_picture_url(event_id: int, user_id: int) -> str:
        EventService.get_event(event_id, user_id, MemberRole.ORGANIZER)
        return storage_backend.generate_event_picture_url(event_id)
