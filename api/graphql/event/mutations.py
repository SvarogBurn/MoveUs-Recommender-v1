from datetime import datetime

import graphene
from django.utils.timezone import now

from api.graphql.event.types import EventMemberType, EventType
from main.chat.services import ChatService
from main.event.models import EventMember, EventMemberLike
from main.event.services import EventService
from main.event.validators import validate_event
from main.location.models import Location
from main.location.validators import validate_location
from main.user.models import User
from shared.enums import ActivityType as Activity
from shared.enums import CountryCode, EventRating, GenderNoPNTS, MemberRole, SkillLevel
from shared.errors.mu_error import MUError, MUErrorCode
from shared.utils.decorators import require_auth


class CreateEventMutation(graphene.Mutation):

    class Arguments:
        title = graphene.String(required=True)
        description = graphene.String(required=False)
        start_time = graphene.DateTime(required=True)
        end_time = graphene.DateTime(required=True)
        requirements = graphene.String(required=False)
        location_id = graphene.Int(required=False)
        location_longitude = graphene.Float(required=False)
        location_latitude = graphene.Float(required=False)
        location_address_line1 = graphene.String(required=False)
        location_address_line2 = graphene.String(required=False)
        location_zip_code = graphene.Int(required=False)
        location_country_code = CountryCode.as_graphene_enum()(required=False)
        location_region = graphene.String(required=False)
        location_name = graphene.String(required=False)
        activity = Activity.as_graphene_enum()(required=True)
        skill_level = SkillLevel.as_graphene_enum()(required=True)
        max_participants = graphene.Int(required=False)
        allow_spectators = graphene.Boolean(required=False)
        min_age = graphene.Int(required=False)
        max_age = graphene.Int(required=False)
        accepted_genders = graphene.List(
            GenderNoPNTS.as_graphene_enum(), required=False
        )

    event = graphene.Field(EventType)

    @require_auth
    def mutate(
        self,
        info: graphene.ResolveInfo,
        title: str = None,
        description: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        requirements: object = None,
        location_id: int = None,
        location_longitude: float = None,
        location_latitude: float = None,
        location_address_line1: str = None,
        location_address_line2: str = None,
        location_zip_code: int = None,
        location_country_code: CountryCode = None,
        location_region: str = None,
        location_name: str = None,
        activity: Activity = None,
        skill_level: SkillLevel = None,
        max_participants: int = None,
        allow_spectators: bool = None,
        min_age: int = None,
        max_age: int = None,
        accepted_genders: list = None,
    ):

        user: User = info.context.user

        if not location_id and not (location_longitude and location_latitude):
            raise MUError(MUErrorCode.MINIMAL_LOCATION_REQUIREMENTS_MISSING)

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
            description,
            start_time,
            end_time,
            max_participants,
            min_age,
            max_age,
            accepted_genders,
        )

        if location_id:
            try:
                location = Location.objects.get(pk=location_id)
            except Location.DoesNotExist:
                raise MUError(MUErrorCode.LOCATION_DOES_NOT_EXIST)
        else:
            location = Location.objects.create(
                longitude=location_longitude,
                latitude=location_latitude,
                address_line_1=location_address_line1,
                address_line_2=location_address_line2,
                zip_code=location_zip_code,
                country_code=location_country_code,
                region=location_region,
                name=location_name,
            )

        kwargs = {}
        if description is not None:
            kwargs["description"] = description
        if requirements is not None:
            kwargs["requirements"] = requirements
        if max_participants is not None:
            kwargs["max_participants"] = max_participants
        if allow_spectators is not None:
            kwargs["allow_spectators"] = allow_spectators
        if min_age is not None:
            kwargs["min_age"] = min_age
        if max_age is not None:
            kwargs["max_age"] = max_age

        event = EventService.create_event(
            user=user,
            title=title,
            start_time=start_time,
            end_time=end_time,
            location=location,
            activity_id=activity,
            skill_level=skill_level,
            **kwargs
        )

        return CreateEventMutation(event=event)


class AlterEventMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)
        title = graphene.String(required=False)
        description = graphene.String(required=False)
        start_time = graphene.DateTime(required=False)
        end_time = graphene.DateTime(required=False)
        requirements = graphene.String(required=False)
        max_participants = graphene.Int(required=False)

    event = graphene.Field(EventType)

    @require_auth
    def mutate(
        self,
        info: graphene.ResolveInfo,
        event_id: str = None,
        title: str = None,
        description: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        requirements: object = None,
        max_participants: int = None,
    ):

        user: User = info.context.user

        validate_event(title, description, start_time, end_time, max_participants)

        event = EventService.get_event(event_id, user.id, MemberRole.ORGANIZER)

        if max_participants and max_participants < event.participant_count():
            raise MUError(MUErrorCode.EVENT_MIN_MAX_PARTICIPANTS)

        EventService.alter_event(
            event,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            requirements=requirements,
            max_participants=max_participants,
        )

        return AlterEventMutation(event=event)


class DeleteEventMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(
        self,
        info: graphene.ResolveInfo,
        event_id: str = None,
    ) -> "DeleteEventMutation":

        user: User = info.context.user

        event = EventService.get_event(event_id, user.id, MemberRole.ORGANIZER)

        EventService.delete_event(event)

        return DeleteEventMutation(success=True)


class JoinEventMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)

    event = graphene.Field(EventType)
    member = graphene.Field(EventMemberType)

    @require_auth
    def mutate(
        self, info: graphene.ResolveInfo, event_id: int
    ) -> "JoinEventMutation":
        user: User = info.context.user
        event = EventService.get_event(event_id)
        member = EventService.join_event(event, user)

        return JoinEventMutation(event=event, member=member)


class SpectateEventMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)

    event = graphene.Field(EventType)
    member = graphene.Field(EventMemberType)

    @require_auth
    def mutate(
        self, info: graphene.ResolveInfo, event_id: int
    ) -> "SpectateEventMutation":
        user: User = info.context.user
        event = EventService.get_event(event_id)

        if event.start_time <= now():
            raise MUError(MUErrorCode.EVENT_ALREADY_STARTED)

        try:
            member = EventMember.objects.get(pk=(user.id, event_id))
            if member.role != MemberRole.PARTICIPANT:
                raise MUError(MUErrorCode.CANNOT_DEMOTE_YOURSELF)
            member.role = MemberRole.SPECTATOR
            member.save()
        except EventMember.DoesNotExist:
            member = EventMember.objects.create(
                user_id=user.id, event_id=event_id, role=MemberRole.SPECTATOR
            )

        return SpectateEventMutation(event=event, member=member)


class LeaveEventMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)

    event = graphene.Field(EventType)

    @require_auth
    def mutate(
        self, info: graphene.ResolveInfo, event_id: int
    ) -> "LeaveEventMutation":
        user: User = info.context.user
        event = EventService.get_event(event_id)

        if event.end_time <= now():
            raise MUError(MUErrorCode.EVENT_ALREADY_ENDED)

        try:
            member = EventMember.objects.get(pk=(user.id, event_id))
            if member.role == MemberRole.ORGANIZER:
                raise MUError(MUErrorCode.CANNOT_LEAVE_AS_ORGANIZATOR)
            member.delete()
            if event.chat_id:
                ChatService.remove_chat_member(event.chat_id, user.id)
        except EventMember.DoesNotExist:
            raise MUError(MUErrorCode.NOT_MEMBER)

        return LeaveEventMutation(event=event)


class KickEventMemberMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)
        user_id = graphene.Int(required=True)

    event = graphene.Field(EventType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, event_id: int, user_id: int):
        user: User = info.context.user

        if user.id == user_id:
            raise MUError(MUErrorCode.CANNOT_KICK_YOURSELF)

        event = EventService.get_event(event_id, user.id, MemberRole.MODERATOR)

        if event.end_time <= now():
            raise MUError(MUErrorCode.EVENT_ALREADY_ENDED)

        try:
            member = EventMember.objects.get(pk=(user_id, event_id))
            if member.role == MemberRole.ORGANIZER:
                raise MUError(MUErrorCode.CANNOT_KICK_ORGANIZER)
            member.delete()
            if event.chat_id:
                ChatService.remove_chat_member(event.chat_id, user_id)
        except EventMember.DoesNotExist:
            raise MUError(MUErrorCode.EVENT_MEMBER_DOES_NOT_EXIST)

        return LeaveEventMutation(event=event)


class ConfirmMemberParticipationMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)
        user_id = graphene.Int(required=True)
        participated = graphene.Boolean(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(
        self,
        info: graphene.ResolveInfo,
        event_id: int,
        user_id: int,
        participated: bool,
    ):
        user: User = info.context.user

        EventService.get_event(event_id, user.id, MemberRole.MODERATOR)

        try:
            member = EventMember.objects.get(pk=(user_id, event_id))
            if member.role == MemberRole.PARTICIPANT:
                member.has_participated = participated
                member.save()
                return ConfirmMemberParticipationMutation(success=True)
        except EventMember.DoesNotExist:
            pass

        raise MUError(MUErrorCode.CANNOT_CONFIRM_NON_PARTICIPATING_MEMBER)


class FinishEventMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(
        self, info: graphene.ResolveInfo, event_id: int
    ) -> "FinishEventMutation":
        user: User = info.context.user
        EventService.finish_event(event_id, user.id)
        return FinishEventMutation(success=True)


class RateEventMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)
        score = EventRating.as_graphene_enum()(required=True)
        comment = graphene.String(required=False)

    event = graphene.Field(EventType)

    @require_auth
    def mutate(
        self,
        info: graphene.ResolveInfo,
        event_id: int,
        score: EventMember,
        comment: str = None,
    ):
        user: User = info.context.user

        event, member = EventService.get_event_with_member(
            event_id, user.id, MemberRole.PARTICIPANT
        )

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

        return RateEventMutation(event=event)


class LikeEventMemberMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)
        user_id = graphene.Int(required=True)
        like = graphene.Boolean(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(
        self, info: graphene.ResolveInfo, event_id: int, user_id: int, like: bool
    ):
        user: User = info.context.user

        if user.id == user_id:
            raise MUError(MUErrorCode.CANNOT_LIKE_YOURSELF)

        event, member = EventService.get_event_with_member(
            event_id, user.id, MemberRole.PARTICIPANT
        )

        if not event.finished:
            raise MUError(MUErrorCode.CANNOT_LIKE_BEFORE_FINISH)

        if not member.has_participated:
            raise MUError(MUErrorCode.CANNOT_LIKE_DIDNT_PARTICIPATE)

        try:
            other = EventMember.objects.get(pk=(user_id, event_id))
            if other.participates and other.has_participated:

                try:
                    eml = EventMemberLike.objects.get(pk=(event_id, user.id, user_id))
                    eml.like = like
                    eml.save()
                except EventMemberLike.DoesNotExist:
                    EventMemberLike.objects.create(
                        user_1_id=user.id,
                        user_2_id=user_id,
                        event_id=event_id,
                        like=like,
                    )

                return LikeEventMemberMutation(success=True)
        except EventMember.DoesNotExist:
            pass

        raise MUError(MUErrorCode.CANNOT_LIKE_NOT_PARTICIPANT)


class Mutation(graphene.ObjectType):
    create_event = CreateEventMutation.Field()
    alter_event = AlterEventMutation.Field()
    delete_event = DeleteEventMutation.Field()
    join_event = JoinEventMutation.Field()
    spectate_event = SpectateEventMutation.Field()
    leave_event = LeaveEventMutation.Field()
    kick_event_member = KickEventMemberMutation.Field()
    confirm_member_participation = ConfirmMemberParticipationMutation.Field()
    finish_event = FinishEventMutation.Field()
    rate_event = RateEventMutation.Field()
    like_event_member = LikeEventMemberMutation.Field()
