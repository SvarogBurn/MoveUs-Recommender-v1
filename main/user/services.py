from main.user.models import User, UserPrivacySetting, UserReport
from main.user.validators import (
    validate_max_travel_distance,
    validate_preferred_event_duration,
    validate_profile,
)
from shared.enums import PrivacyScope, PrivacySetting
from shared.errors.mu_error import MUError, MUErrorCode


class UserService:
    @staticmethod
    def initialize_privacy_settings(user: User) -> None:
        for key in PrivacySetting:
            UserPrivacySetting.objects.create(
                user=user, setting=key.value, scope=PrivacyScope.EVERYONE
            )

    @staticmethod
    def alter_basic_info(user: User, **fields) -> None:
        validate_profile(
            fields.get("first_name"),
            fields.get("last_name"),
            fields.get("date_of_birth"),
            fields.get("bio"),
        )
        for field, value in fields.items():
            if value is not None:
                setattr(user, field, value)
        user.save()

    @staticmethod
    def alter_survey_info(user: User, **fields) -> None:
        validate_preferred_event_duration(fields.get("preferred_event_duration"))
        for field, value in fields.items():
            if value is not None:
                setattr(user, field, value)
        user.save()

    @staticmethod
    def alter_max_travel_distance(user: User, distance: int = None) -> None:
        validate_max_travel_distance(distance)
        user.max_travel_distance = distance
        user.save()

    @staticmethod
    def alter_all_privacy_settings(user_id: int, scope: PrivacyScope) -> None:
        UserPrivacySetting.objects.filter(user_id=user_id).update(scope=scope)

    @staticmethod
    def report_user(
        reporter_id: int, reported_id: int, comment: str = None
    ) -> None:
        if comment and len(comment) > 512:
            raise MUError(MUErrorCode.REPORT_COMMENT_MAX_LENGTH)

        if reporter_id == reported_id:
            raise MUError(MUErrorCode.CANNOT_TARGET_SELF)

        try:
            User.objects.get(pk=reported_id)
        except User.DoesNotExist:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)

        UserReport.objects.create(
            reporter_id=reporter_id, reported_id=reported_id, comment=comment
        )
