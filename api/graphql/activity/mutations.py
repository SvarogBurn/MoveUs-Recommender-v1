import graphene

from api.graphql.activity.types import PreferredActivityType
from main.activity.services import ActivityService
from main.user.models import User
from shared.enums import ActivityKind as Activity
from shared.enums import SkillLevel
from shared.utils.decorators import require_auth


class SetPreferredActivity(graphene.Mutation):

    class Arguments:
        activity = Activity.as_graphene_enum()()
        skill_level = SkillLevel.as_graphene_enum()()

    success = graphene.Boolean()

    @require_auth
    def mutate(
        cls, root, info: graphene.ResolveInfo, activity: Activity, skill_level: SkillLevel
    ):

        user: User = info.context.user
        ActivityService.set_preferred_activity(user, activity, skill_level)
        return SetPreferredActivity(success=True)


class RemovePreferredActivity(graphene.Mutation):

    class Arguments:
        activity = Activity.as_graphene_enum()()

    success = graphene.Boolean()

    @require_auth
    def mutate(cls, root, info: graphene.ResolveInfo, activity: Activity):

        user: User = info.context.user
        ActivityService.remove_preferred_activity(user, activity)
        return RemovePreferredActivity(success=True)


class Mutation(graphene.ObjectType):
    set_preferred_activity = SetPreferredActivity.Field()
    remove_preferred_activity = RemovePreferredActivity.Field()
