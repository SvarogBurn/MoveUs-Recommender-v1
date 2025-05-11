import graphene

from ...models import Activity
from .types import ActivityType


class ActivityQuery(graphene.ObjectType):
    all_activities = graphene.List(ActivityType)
    
    def resolve_all_activities(root, info):
        return Activity.objects.all()