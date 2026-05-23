import graphene

from api.graphql.event.types import EventType
from api.graphql.social.types import PostType


class FeedItemUnion(graphene.Union):
    class Meta:
        types = (PostType, EventType)
