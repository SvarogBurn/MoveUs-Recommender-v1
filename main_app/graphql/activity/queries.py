import graphene

from .types import ActivityType
from ...models import Activity

class ActivityQuery(graphene.ObjectType):
    all_activities = graphene.List(ActivityType)
    
    def resolve_all_activities(root, info):
        return Activity.objects.all()