from main.activity.models import Activity
from main.user.models import UserPreferences, UserPreferredActivity
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
        preferences, _ = UserPreferences.objects.get_or_create(user_id=user_id)
        UserPreferredActivity.objects.update_or_create(
            preferences=preferences,
            activity_id=activity,
            defaults={"skill_level": skill_level},
        )

    @staticmethod
    def remove_preferred_activity(user_id: int, activity: ActivityKind) -> None:
        try:
            pa = UserPreferredActivity.objects.get(
                preferences__user_id=user_id, activity_id=activity
            )
            pa.delete()
        except UserPreferredActivity.DoesNotExist:
            raise MUError(MUErrorCode.PREFERRED_ACTIVITY_DOES_NOT_EXIST)
