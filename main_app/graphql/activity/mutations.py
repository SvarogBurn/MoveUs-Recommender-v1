import graphene

from main_app.util import require_auth

from ...models import PreferredActivity, User
from ...models.enums import Activity, SkillLevel
from ..activity.types import PreferredActivityType
from ..error import MUError, MUErrorCode


class SetPreferredActivity(graphene.Mutation):

    class Arguments:
        activity = Activity.as_graphene_enum()()
        skill_level = SkillLevel.as_graphene_enum()()

    success = graphene.Boolean()

    @require_auth
    def mutate(
        cls,
        root,
        info,
        activity: Activity,
        skill_level: SkillLevel
    ):
        
        user: User = info.context.user

        try:
            pa = PreferredActivity.objects.get(pk = (user.id, activity))
            pa.skill_level = skill_level
            pa.save()
        except PreferredActivity.DoesNotExist:
            PreferredActivity.objects.create(
                activity_id = activity,
                user_id = user.id,
                skill_level = skill_level
            )

        return SetPreferredActivity(success = True)        

class RemovePreferredActivity(graphene.Mutation):

    class Arguments:
        activity = Activity.as_graphene_enum()()

    success = graphene.Boolean()

    @require_auth
    def mutate(
        cls,
        root,
        info,
        activity: Activity
    ):
        
        user: User = info.context.user

        try:
            pa = PreferredActivity.objects.get(pk = (user.id, activity))
            pa.delete()
        except PreferredActivity.DoesNotExist:
            raise MUError(MUErrorCode.PREFERRED_ACTIVITY_DOES_NOT_EXIST)

        return RemovePreferredActivity(success = True)   

class Mutation(graphene.ObjectType):
    set_preferred_activity = SetPreferredActivity.Field()
    remove_preferred_activity = RemovePreferredActivity.Field()
