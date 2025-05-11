import graphene
from django.db.models import Q

from main_app.util import require_auth

from ...models import Relationship
from ...models.enums import RelationshipStatus
from .types import RelationshipType


class RelationshipQuery (graphene.ObjectType):
    requests_sent = graphene.List(RelationshipType)
    count_requests_sent = graphene.Int()

    requests_pending = graphene.List(RelationshipType)
    count_requests_pending = graphene.Int()

    friends = graphene.List(RelationshipType)
    count_friends = graphene.Int()

    @require_auth
    def resolve_requests_sent(root, info):
        return Relationship.objects.filter(user_1 = info.context.user, status = RelationshipStatus.PENDING)
    
    @require_auth
    def resolve_count_requests_sent(root, info):
        return Relationship.objects.filter(user_1 = info.context.user, status = RelationshipStatus.PENDING).count()
    
    @require_auth
    def resolve_requests_pending(root, info):
        return Relationship.objects.filter(user_2 = info.context.user, status = RelationshipStatus.PENDING)
    
    @require_auth
    def resolve_count_requests_pending(root, info):
        return Relationship.objects.filter(user_2 = info.context.user, status = RelationshipStatus.PENDING).count()
    
    @require_auth
    def resolve_friends(root, info):
        q1 = Q(user_1 = info.context.user)
        q2 = Q(user_2 = info.context.user)

        return Relationship.objects.filter(q1 | q2, status = RelationshipStatus.FRIENDS)
    
    @require_auth
    def resolve_count_friends(root, info):
        q1 = Q(user_1 = info.context.user)
        q2 = Q(user_2 = info.context.user)

        return Relationship.objects.filter(q1 | q2, status = RelationshipStatus.FRIENDS).count()