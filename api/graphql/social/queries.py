import graphene
from django.db.models import Q

from api.graphql.social.types import PostType, RelationshipType
from main.social.models import Post, Relationship
from shared.enums import RelationshipStatus
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
        return Relationship.objects.filter(
            user_1=info.context.user, status=RelationshipStatus.PENDING
        )

    @require_auth
    def resolve_count_requests_sent(root, info: graphene.ResolveInfo) -> int:
        return Relationship.objects.filter(
            user_1=info.context.user, status=RelationshipStatus.PENDING
        ).count()

    @require_auth
    def resolve_requests_pending(root, info: graphene.ResolveInfo):
        return Relationship.objects.filter(
            user_2=info.context.user, status=RelationshipStatus.PENDING
        )

    @require_auth
    def resolve_count_requests_pending(root, info: graphene.ResolveInfo) -> int:
        return Relationship.objects.filter(
            user_2=info.context.user, status=RelationshipStatus.PENDING
        ).count()

    @require_auth
    def resolve_friends(root, info: graphene.ResolveInfo):
        q1 = Q(user_1=info.context.user)
        q2 = Q(user_2=info.context.user)

        return Relationship.objects.filter(q1 | q2, status=RelationshipStatus.FRIENDS)

    @require_auth
    def resolve_count_friends(root, info: graphene.ResolveInfo) -> int:
        q1 = Q(user_1=info.context.user)
        q2 = Q(user_2=info.context.user)

        return Relationship.objects.filter(
            q1 | q2, status=RelationshipStatus.FRIENDS
        ).count()
    

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
