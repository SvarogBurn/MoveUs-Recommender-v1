import graphene
from ..object_type import MUObjectType

from ...models import Event, EventMember
from ...models.enums import MemberRole
from ..post.types import PostType
from ..user.types import UserType

class EventMemberType(MUObjectType):
    
    class Meta:
        model = EventMember
        exclude = ("pk",)

class EventType(MUObjectType):
    posts = graphene.List(PostType)
    organizer = graphene.Field(EventMemberType)
    participants = graphene.List(EventMemberType)
    moderators = graphene.List(EventMemberType)
    spectators = graphene.List(EventMemberType)

    class Meta:
        model = Event
        exclude = ("post_set",)

    def resolve_posts(self: Event, info):
        return self.post_set;

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


