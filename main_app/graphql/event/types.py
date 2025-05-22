import graphene
from django.db.models import Avg

from main_app.graphql.event_member.types import EventMemberType
from main_app.graphql.post_event.types import EventCommentType

from ...models import Event, EventMember
from ...models.enums import MemberRole
from ..object_type import MUObjectType


class EventTypeMixin(MUObjectType):
    organizer = graphene.Field(EventMemberType)
    participants = graphene.List(EventMemberType)
    moderators = graphene.List(EventMemberType)
    spectators = graphene.List(EventMemberType)
    participant_count = graphene.Int()
    role = graphene.Field(MemberRole.as_graphene_enum())
    average_score = graphene.Float()
    comments = graphene.List(EventCommentType)

    class Meta:
        model = Event

    def resolve_organizer(self: Event, info):
        return EventMember.objects.filter(
            event = self,
            role = MemberRole.ORGANIZER
        )[0]
    
    def resolve_participants(self: Event, info):
        return EventMember.objects.filter(
            event = self,
            role = MemberRole.PARTICIPANT
        )
    
    def resolve_moderators(self: Event, info):
        return EventMember.objects.filter(
            event = self,
            role = MemberRole.MODERATOR
        )
    
    def resolve_spectators(self: Event, info):
        return EventMember.objects.filter(
            event = self,
            role = MemberRole.SPECTATOR
        )
    
    def resolve_participant_count(self: Event, info):
        return EventMember.objects.filter(
            event = self,
            participates = True
        ).count()
    
    def resolve_role(self: Event, info):
        user_id = info.context.user.id;
        if id == None:
            return None
        try:
            return EventMember.objects.get(
                pk = (user_id, self.id)
            ).role;
        except EventMember.DoesNotExist:
            return None
        
    def resolve_average_score(self: Event, info):
        score = EventMember.objects.filter(
                event_id=self.id
            ).aggregate(
                Avg('score')
            )['score__avg'];
        if score is not None:
            return score + 1
        return None
    
    def resolve_comments(self: Event, info):
        return [
            EventCommentType(
                member=m,
                comment=m.comment
            ) for m in EventMember.objects.filter(
                event_id = self.id,
                comment__isnull = False
            )
        ]

class UnfinishedEventType(EventTypeMixin):
    class Meta:
        model = Event

    unconfirmed_participants = graphene.List(EventMemberType)

    def resolve_unconfirmed_participants(self: Event, info):
        return EventMember.objects.filter(
            event_id = self.id,
            participates = True,
            has_participated__isnull = True
        );

class EventType(EventTypeMixin):
    class Meta:
        model = Event
