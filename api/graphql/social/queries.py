import graphene

from api.graphql.social.types import FollowType, PostType
from main.social.models import Post
from main.social.services import FollowService
from shared.utils.decorators import require_auth


class FollowQuery(graphene.ObjectType):
    followers = graphene.List(FollowType)
    follower_count = graphene.Int()
    following = graphene.List(FollowType)
    following_count = graphene.Int()

    @require_auth
    def resolve_followers(root, info: graphene.ResolveInfo):
        return FollowService.get_followers(info.context.user)

    @require_auth
    def resolve_follower_count(root, info: graphene.ResolveInfo) -> int:
        return FollowService.get_followers(info.context.user).count()

    @require_auth
    def resolve_following(root, info: graphene.ResolveInfo):
        return FollowService.get_following(info.context.user)

    @require_auth
    def resolve_following_count(root, info: graphene.ResolveInfo) -> int:
        return FollowService.get_following(info.context.user).count()


class PostQuery(graphene.ObjectType):
    post = graphene.Field(PostType, id=graphene.Int())

    def resolve_post(root, info: graphene.ResolveInfo, id: int) -> Post:
        return Post.objects.select_related("author").get(pk=id)
