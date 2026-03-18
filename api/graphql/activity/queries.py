import graphene

from api.graphql.activity.types import ActivityModelType
from main.activity.services import ActivityService


class ActivityQuery(graphene.ObjectType):
    all_activities = graphene.List(ActivityModelType)

    def resolve_all_activities(root, info: graphene.ResolveInfo):
        return ActivityService.get_all()
