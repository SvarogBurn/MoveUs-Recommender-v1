import graphene
from graphene_django import DjangoObjectType

from ...models import Event, EventMember, EventActivity
from ..post.types import PostType
from ..user.types import UserType

# class EventMemberType(DjangoObjectType):
    
#     class Meta:
#         model = EventMember

class EventType(DjangoObjectType):
    posts = graphene.List(PostType)
    # members = graphene.List(EventMemberType)

    class Meta:
        model = Event
        exclude = ("post_set", "event_member_set")

    def resolve_posts(self: Event, info):
        return self.post_set;

    def resolve_members(self: EventMember, info):
        return self.event_member_set;
