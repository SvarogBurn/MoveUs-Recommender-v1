import graphene

from api.graphql.social.types import FollowType, PostType
from main.social.models import Post
from main.social.services import FollowService, PostService
from shared.utils.decorators import require_auth


class FollowQuery(graphene.ObjectType):
    followers = graphene.List(FollowType)
    follower_count = graphene.Int()
    following = graphene.List(FollowType)
    following_count = graphene.Int()

    @require_auth
    def resolve_followers(root, info: graphene.ResolveInfo):
        return FollowService.get_followers(info.context.user.id)

    @require_auth
    def resolve_follower_count(root, info: graphene.ResolveInfo) -> int:
        return FollowService.get_follower_count(info.context.user.id)

    @require_auth
    def resolve_following(root, info: graphene.ResolveInfo):
        return FollowService.get_following(info.context.user.id)

    @require_auth
    def resolve_following_count(root, info: graphene.ResolveInfo) -> int:
        return FollowService.get_following_count(info.context.user.id)


class PostQuery(graphene.ObjectType):
    post = graphene.Field(PostType, id=graphene.Int())

    def resolve_post(root, info: graphene.ResolveInfo, id: int) -> Post:
        viewer_id = info.context.user.id or None
        return PostService.get_post(id, viewer_id=viewer_id)
