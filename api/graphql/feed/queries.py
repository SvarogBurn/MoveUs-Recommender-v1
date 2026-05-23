import graphene

from main.feed.services import FeedService
from shared.utils.decorators import require_auth

from .types import FeedItemUnion


class FeedQuery(graphene.ObjectType):
    my_feed = graphene.List(
        FeedItemUnion,
        start=graphene.Int(required=True),
        end=graphene.Int(required=True),
    )

    @require_auth
    def resolve_my_feed(root, info: graphene.ResolveInfo, start: int, end: int):
        return FeedService.get_feed(info.context.user.id, start, end)
