from main.activity.models import Activity
from main.user.models import PreferredActivity
from shared.enums import ActivityKind, SkillLevel
from shared.errors.mu_error import MUError, MUErrorCode


class ActivityService:

    @staticmethod
    def get_all() -> list[Activity]:
        return Activity.objects.all()

    @staticmethod
    def set_preferred_activity(
        user_id: int, activity: ActivityKind, skill_level: SkillLevel
    ) -> None:
        try:
            pa = PreferredActivity.objects.get(pk=(user_id, activity))
            pa.skill_level = skill_level
            pa.save()
        except PreferredActivity.DoesNotExist:
            PreferredActivity.objects.create(
                activity_id=activity, user_id=user_id, skill_level=skill_level
            )

    @staticmethod
    def remove_preferred_activity(user_id: int, activity: ActivityKind) -> None:
        try:
            pa = PreferredActivity.objects.get(pk=(user_id, activity))
            pa.delete()
        except PreferredActivity.DoesNotExist:
            raise MUError(MUErrorCode.PREFERRED_ACTIVITY_DOES_NOT_EXIST)
