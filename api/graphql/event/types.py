import graphene
from django.db.models import Avg

from api.graphql.object_type import MUObjectType
from api.graphql.social.types import CommentType
from main.event.models import Event, EventMember
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
        if members is not None:
            result = [m for m in members if m.role == MemberRole.ORGANIZER]
            return result[0] if result else None
        return EventMember.objects.filter(event=self, role=MemberRole.ORGANIZER).first()

    def resolve_participants(
        self: Event, info: graphene.ResolveInfo
    ) -> list[EventMember]:
        members = getattr(self, "_members", None)
        if members is not None:
            return [m for m in members if m.role == MemberRole.PARTICIPANT]
        return EventMember.objects.filter(event=self, role=MemberRole.PARTICIPANT)

    def resolve_moderators(
        self: Event, info: graphene.ResolveInfo
    ) -> list[EventMember]:
        members = getattr(self, "_members", None)
        if members is not None:
            return [m for m in members if m.role == MemberRole.MODERATOR]
        return EventMember.objects.filter(event=self, role=MemberRole.MODERATOR)

    def resolve_spectators(
        self: Event, info: graphene.ResolveInfo
    ) -> list[EventMember]:
        members = getattr(self, "_members", None)
        if members is not None:
            return [m for m in members if m.role == MemberRole.SPECTATOR]
        return EventMember.objects.filter(event=self, role=MemberRole.SPECTATOR)

    def resolve_participant_count(self: Event, info: graphene.ResolveInfo) -> int:
        members = getattr(self, "_members", None)
        if members is not None:
            return len(members)
        return EventMember.objects.filter(event=self).count()

    def resolve_role(self: Event, info: graphene.ResolveInfo) -> int | None:
        user_id = info.context.user.id
        if not user_id:
            return None
        members = getattr(self, "_members", None)
        if members is not None:
            result = [m for m in members if m.user_id == user_id]
            return result[0].role if result else None
        try:
            return EventMember.objects.get(pk=(user_id, self.id)).role
        except EventMember.DoesNotExist:
            return None

    def resolve_average_score(self: Event, info: graphene.ResolveInfo) -> float | None:
        members = getattr(self, "_members", None)
        if members is not None:
            scores = [m.score for m in members if m.score is not None]
            return (sum(scores) / len(scores) + 1) if scores else None
        score = EventMember.objects.filter(event_id=self.id).aggregate(Avg("score"))[
            "score__avg"
        ]
        return score + 1 if score is not None else None

    def resolve_reviews(
        self: Event, info: graphene.ResolveInfo
    ) -> list[EventReviewType]:
        members = getattr(self, "_members", None)
        if members is not None:
            source = [m for m in members if m.comment is not None]
        else:
            source = EventMember.objects.filter(event_id=self.id, comment__isnull=False)
        return [EventReviewType(member=m, comment=m.comment) for m in source]

    def resolve_comments(
        self: Event, info: graphene.ResolveInfo, start: int, end: int
    ):
        return CommentService.get_comments_for_event(self, start, end)


class UnfinishedEventType(EventTypeMixin):
    class Meta:
        model = Event

    unconfirmed_participants = graphene.List(EventMemberType)

    def resolve_unconfirmed_participants(self: Event, info: graphene.ResolveInfo):
        return EventMember.objects.filter(
            event_id=self.id, participates=True, has_participated__isnull=True
        )


class EventType(EventTypeMixin):
    class Meta:
        model = Event
