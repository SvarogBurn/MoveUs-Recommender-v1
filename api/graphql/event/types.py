import graphene

from api.graphql.object_type import MUObjectType
from api.graphql.social.types import CommentType
from main.event.models import Event, EventMember
from main.event.services import EventService
from main.social.services import CommentService
from shared.enums import EventPhase, MemberRole


def _can_view_member_rating(
    member: EventMember, info: graphene.ResolveInfo
) -> bool:
    """A member's score/comment is visible only to the member themselves and
    to organizers of the event. The organizer check is memoized per request to
    avoid an N+1 query across member lists."""
    requester_id = info.context.user.id
    if not requester_id:
        return False
    if requester_id == member.user_id:
        return True
    cache = getattr(info.context, "_event_organizer_cache", None)
    if cache is None:
        cache = {}
        info.context._event_organizer_cache = cache
    key = (member.event_id, requester_id)
    if key not in cache:
        cache[key] = EventService.is_organizer(member.event_id, requester_id)
    return cache[key]


class EventMemberType(MUObjectType):
    score = graphene.String()

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

    def resolve_score(self: EventMember, info: graphene.ResolveInfo) -> str | None:
        if _can_view_member_rating(self, info):
            return self.get_score_display()

    def resolve_comment(
        self: EventMember, info: graphene.ResolveInfo
    ) -> str | None:
        if _can_view_member_rating(self, info):
            return self.comment


class EventTypeMixin(MUObjectType):
    organizer = graphene.Field(EventMemberType)
    participants = graphene.List(EventMemberType)
    moderators = graphene.List(EventMemberType)
    spectators = graphene.List(EventMemberType)
    participant_count = graphene.Int()
    role = graphene.Field(MemberRole.as_graphene_enum())
    phase = graphene.Field(EventPhase.as_graphene_enum(), required=True)
    score = graphene.Float()
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

    def resolve_phase(self: Event, info: graphene.ResolveInfo) -> int:
        return self.phase

    def resolve_score(self: Event, info: graphene.ResolveInfo) -> float | None:
        members = getattr(self, "_members", None)
        return EventService.get_score(self.id, members)

    def resolve_comments(
        self: Event, info: graphene.ResolveInfo, start: int, end: int
    ):
        viewer_id = info.context.user.id or None
        return CommentService.get_comments_for_event(
            self.id, start, end, viewer_id=viewer_id
        )


class UnfinishedEventType(EventTypeMixin):
    class Meta:
        model = Event

    unconfirmed_participants = graphene.List(EventMemberType)

    def resolve_unconfirmed_participants(self: Event, info: graphene.ResolveInfo):
        return EventService.get_unconfirmed_participants(self.id)


class EventType(EventTypeMixin):
    class Meta:
        model = Event
