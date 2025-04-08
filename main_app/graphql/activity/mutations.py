import graphene

from main_app.graphql.user.types import ProfileType
from main_app.validators import profile_validator

from ..error import MUError, MUErrorCode
from ..activity.types import PreferredActivityType
from ...models import User, PreferredActivity
from ...models.enums import SkillLevel, ActivityEnum

class SetPreferredActivity(graphene.Mutation):

    class Arguments:
        activity = ActivityEnum.as_graphene_enum()()
        skill_level = SkillLevel.as_graphene_enum()()

    preferred_activities = graphene.List(PreferredActivityType)

    @classmethod
    def mutate(
        cls,
        root,
        info,
        activity: ActivityEnum,
        skill_level: SkillLevel
    ):
        
        user: User = info.context.user
        if not user.id: raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)

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

        return SetPreferredActivity(
            preferred_activities = PreferredActivity.objects.filter(user = user)
        )        

class RemovePreferredActivity(graphene.Mutation):

    class Arguments:
        activity = ActivityEnum.as_graphene_enum()()

    preferred_activities = graphene.List(PreferredActivityType)

    @classmethod
    def mutate(
        cls,
        root,
        info,
        activity: ActivityEnum
    ):
        
        user: User = info.context.user
        if not user.id: raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)

        try:
            pa = PreferredActivity.objects.get(pk = (user.id, activity))
            pa.delete()
        except PreferredActivity.DoesNotExist:
            raise MUError(MUErrorCode.PREFERRED_ACTIVITY_DOES_NOT_EXIST)

        return RemovePreferredActivity(
            preferred_activities = PreferredActivity.objects.filter(user = user)
        )   

class Mutation(graphene.ObjectType):
    set_preferred_activity = SetPreferredActivity.Field()
    remove_preferred_activity = RemovePreferredActivity.Field()
