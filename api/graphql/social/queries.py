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
    event_posts = graphene.List(
        PostType,
        event_id=graphene.String(default_value=None),
        start=graphene.Int(default_value=0),
        end=graphene.Int(default_value=10),
    )
    global_posts = graphene.List(
        PostType,
        start=graphene.Int(default_value=0),
        end=graphene.Int(default_value=10),
    )

    def resolve_post(root, info: graphene.ResolveInfo, id: int) -> Post:
        return Post.objects.get(pk=id)

    def resolve_event_posts(
        root, info: graphene.ResolveInfo, event_id: str | None, start: int, end: int
    ):
        if event_id:
            return Post.objects.filter(event=event_id).order_by("-time_posted")[
                start:end
            ]
        return Post.objects.filter(event__isnull=False).order_by("-time_posted")[
            start:end
        ]

    def resolve_global_posts(root, info: graphene.ResolveInfo, start: int, end: int):
        return Post.objects.order_by("-time_posted")[start:end]
