import graphene

from api.graphql.object_type import MUObjectType
from api.graphql.social.types import CommentType
from main.event.models import Event, EventMember
from main.event.services import EventService
from main.social.services import CommentService
from shared.enums import MemberRole


class EventMemberType(MUObjectType):

    class Meta:
        model = EventMember
        fields = (
            "user",
            "role",
            "participates",
            "has_participated",
            "score",
            "comment",
        )


class EventReviewType(graphene.ObjectType):
    member = graphene.Field(EventMemberType)
    comment = graphene.String()


class EventTypeMixin(MUObjectType):
    organizer = graphene.Field(EventMemberType)
    participants = graphene.List(EventMemberType)
    moderators = graphene.List(EventMemberType)
    spectators = graphene.List(EventMemberType)
    participant_count = graphene.Int()
    role = graphene.Field(MemberRole.as_graphene_enum())
    average_score = graphene.Float()
    reviews = graphene.List(EventReviewType)
    comments = graphene.List(
        CommentType,
        start=graphene.Int(default_value=0),
        end=graphene.Int(default_value=10),
    )

    class Meta:
        model = Event

    def resolve_organizer(
        self: Event, info: graphene.ResolveInfo
    ) -> EventMember | None:
        members = getattr(self, "_members", None)
        return EventService.get_organizer(self.id, members)

    def resolve_participants(
        self: Event, info: graphene.ResolveInfo
    ) -> list[EventMember]:
        members = getattr(self, "_members", None)
        return EventService.get_members_by_role(self.id, MemberRole.PARTICIPANT, members)

    def resolve_moderators(
        self: Event, info: graphene.ResolveInfo
    ) -> list[EventMember]:
        members = getattr(self, "_members", None)
        return EventService.get_members_by_role(self.id, MemberRole.MODERATOR, members)

    def resolve_spectators(
        self: Event, info: graphene.ResolveInfo
    ) -> list[EventMember]:
        members = getattr(self, "_members", None)
        return EventService.get_members_by_role(self.id, MemberRole.SPECTATOR, members)

    def resolve_participant_count(self: Event, info: graphene.ResolveInfo) -> int:
        members = getattr(self, "_members", None)
        return EventService.get_member_count(self.id, members)

    def resolve_role(self: Event, info: graphene.ResolveInfo) -> int | None:
        members = getattr(self, "_members", None)
        return EventService.get_user_role(self.id, info.context.user.id, members)

    def resolve_average_score(self: Event, info: graphene.ResolveInfo) -> float | None:
        members = getattr(self, "_members", None)
        return EventService.get_average_score(self.id, members)

    def resolve_reviews(
        self: Event, info: graphene.ResolveInfo
    ) -> list[EventReviewType]:
        members = getattr(self, "_members", None)
        source = EventService.get_reviews(self.id, members)
        return [EventReviewType(member=m, comment=m.comment) for m in source]

    def resolve_comments(
        self: Event, info: graphene.ResolveInfo, start: int, end: int
    ):
        return CommentService.get_comments_for_event(self.id, start, end)


class UnfinishedEventType(EventTypeMixin):
    class Meta:
        model = Event

    unconfirmed_participants = graphene.List(EventMemberType)

    def resolve_unconfirmed_participants(self: Event, info: graphene.ResolveInfo):
        return EventService.get_unconfirmed_participants(self.id)


class EventType(EventTypeMixin):
    class Meta:
        model = Event
