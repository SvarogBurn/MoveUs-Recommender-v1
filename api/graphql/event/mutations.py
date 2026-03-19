from datetime import datetime

import graphene

from api.graphql.event.types import EventMemberType, EventType
from main.event.services import EventService
from main.user.models import User
from shared.enums import ActivityKind as Activity
from shared.enums import CountryCode, EventRating, GenderNoPNTS, MemberRole, SkillLevel
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
            location_id=location_id,
            location_longitude=location_longitude,
            location_latitude=location_latitude,
            location_address_line1=location_address_line1,
            location_address_line2=location_address_line2,
            location_zip_code=location_zip_code,
            location_country_code=location_country_code,
            location_region=location_region,
            location_name=location_name,
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

        event = EventService.get_event(event_id, user.id, MemberRole.ORGANIZER)

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
        member = EventService.spectate_event(event, user)

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
        EventService.leave_event(event, user)

        return LeaveEventMutation(event=event)


class KickEventMemberMutation(graphene.Mutation):

    class Arguments:
        event_id = graphene.Int(required=True)
        user_id = graphene.Int(required=True)

    event = graphene.Field(EventType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, event_id: int, user_id: int):
        user: User = info.context.user

        event = EventService.get_event(event_id, user.id, MemberRole.MODERATOR)
        EventService.kick_member(event, user.id, user_id)

        return KickEventMemberMutation(event=event)


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

        EventService.confirm_participation(
            user_id, event_id, participated, user.id
        )

        return ConfirmMemberParticipationMutation(success=True)


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
        score: EventRating,
        comment: str = None,
    ):
        user: User = info.context.user

        event, member = EventService.get_event_with_member(
            event_id, user.id, MemberRole.PARTICIPANT
        )

        EventService.rate_event(event, member, score, comment)

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

        event, member = EventService.get_event_with_member(
            event_id, user.id, MemberRole.PARTICIPANT
        )

        EventService.like_member(event, member, user.id, user_id, like)

        return LikeEventMemberMutation(success=True)


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
