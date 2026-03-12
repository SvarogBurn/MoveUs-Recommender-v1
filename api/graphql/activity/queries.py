import graphene

from api.graphql.activity.types import ActivityModelType
from main.activities.models import Activity


class ActivityQuery(graphene.ObjectType):
    all_activities = graphene.List(ActivityModelType)

    def resolve_all_activities(root, info: graphene.ResolveInfo):
        return Activity.objects.all()
