import graphene

from api.graphql.social.types import PostType, RelationshipType
from main.social.models import Post
from main.social.services import RelationshipService
from shared.utils.decorators import require_auth


class RelationshipQuery(graphene.ObjectType):
    requests_sent = graphene.List(RelationshipType)
    count_requests_sent = graphene.Int()

    requests_pending = graphene.List(RelationshipType)
    count_requests_pending = graphene.Int()

    friends = graphene.List(RelationshipType)
    count_friends = graphene.Int()

    @require_auth
    def resolve_requests_sent(root, info: graphene.ResolveInfo):
        return RelationshipService.get_requests_sent(info.context.user)

    @require_auth
    def resolve_count_requests_sent(root, info: graphene.ResolveInfo) -> int:
        return RelationshipService.get_requests_sent(info.context.user).count()

    @require_auth
    def resolve_requests_pending(root, info: graphene.ResolveInfo):
        return RelationshipService.get_requests_pending(info.context.user)

    @require_auth
    def resolve_count_requests_pending(root, info: graphene.ResolveInfo) -> int:
        return RelationshipService.get_requests_pending(info.context.user).count()

    @require_auth
    def resolve_friends(root, info: graphene.ResolveInfo):
        return RelationshipService.get_friends(info.context.user)

    @require_auth
    def resolve_count_friends(root, info: graphene.ResolveInfo) -> int:
        return RelationshipService.get_friends(info.context.user).count()


class PostQuery(graphene.ObjectType):
    post = graphene.Field(PostType, id=graphene.Int())

    def resolve_post(root, info: graphene.ResolveInfo, id: int) -> Post:
        return Post.objects.select_related("author").get(pk=id)
