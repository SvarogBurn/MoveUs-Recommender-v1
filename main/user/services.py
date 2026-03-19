from main.social.validators import validate_comment_length, validate_not_self
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
    def get_user(id: int = None, username: str = None) -> User:
        if not id and not username:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)
        if id and username:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)
        try:
            if id:
                return User.objects.get(pk=id)
            else:
                return User.objects.get(username=username)
        except User.DoesNotExist:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)

    @staticmethod
    def check_privacy(user_id: int, viewer_id: int, setting: PrivacySetting) -> bool:
        if user_id == viewer_id:
            return True
        ups = UserPrivacySetting.objects.filter(
            user_id=user_id, setting=setting
        ).first()
        if not ups or ups.scope == PrivacyScope.EVERYONE:
            return True
        if ups.scope == PrivacyScope.FOLLOWERS:
            from main.social.services import FollowService

            return FollowService.are_mutual(user_id, viewer_id)
        return False

    @staticmethod
    def get_event_likes_count(user_id: int) -> int:
        from main.event.models import EventMemberLike

        return EventMemberLike.objects.filter(user_2_id=user_id, like=True).count()

    @staticmethod
    def get_event_dislikes_count(user_id: int) -> int:
        from main.event.models import EventMemberLike

        return EventMemberLike.objects.filter(user_2_id=user_id, like=False).count()

    @staticmethod
    def initialize_privacy_settings(user_id: int) -> None:
        for key in PrivacySetting:
            UserPrivacySetting.objects.create(
                user_id=user_id, setting=key.value, scope=PrivacyScope.EVERYONE
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
        validate_comment_length(comment, MUErrorCode.REPORT_COMMENT_MAX_LENGTH)

        validate_not_self(reporter_id, reported_id)

        try:
            User.objects.get(pk=reported_id)
        except User.DoesNotExist:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)

        UserReport.objects.create(
            reporter_id=reporter_id, reported_id=reported_id, comment=comment
        )
