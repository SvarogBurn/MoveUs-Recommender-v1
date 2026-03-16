from main.user.models import PreferredActivity, User
from shared.enums import ActivityKind, SkillLevel
from shared.errors.mu_error import MUError, MUErrorCode


class ActivityService:
    @staticmethod
    def set_preferred_activity(
        user: User, activity: ActivityKind, skill_level: SkillLevel
    ) -> None:
        try:
            pa = PreferredActivity.objects.get(pk=(user.id, activity))
            pa.skill_level = skill_level
            pa.save()
        except PreferredActivity.DoesNotExist:
            PreferredActivity.objects.create(
                activity_id=activity, user_id=user.id, skill_level=skill_level
            )

    @staticmethod
    def remove_preferred_activity(user: User, activity: ActivityKind) -> None:
        try:
            pa = PreferredActivity.objects.get(pk=(user.id, activity))
            pa.delete()
        except PreferredActivity.DoesNotExist:
            raise MUError(MUErrorCode.PREFERRED_ACTIVITY_DOES_NOT_EXIST)
