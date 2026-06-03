from django.db import transaction

from main.social.validators import validate_comment_length, validate_not_self
from main.user.models import (
    User,
    UserAvailability,
    UserParticipationGroup,
    UserPreferences,
    UserPreferredActivity,
    UserPrivacySetting,
    UserReport,
)
from main.user.validators import (
    validate_max_travel_distance,
    validate_preferences,
    validate_profile,
)
from shared.enums import PrivacyScope, PrivacySetting
from shared.errors.mu_error import MUError, MUErrorCode

DEFAULT_PRIVACY_SCOPES = {
    PrivacySetting.LOCATION: PrivacyScope.FOLLOWERS,
    PrivacySetting.AGE: PrivacyScope.FOLLOWERS,
    PrivacySetting.GENDER: PrivacyScope.FOLLOWERS,
    PrivacySetting.FOLLOWERS: PrivacyScope.EVERYONE,
    PrivacySetting.POSTS: PrivacyScope.EVERYONE,
}


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
    def get_privacy_map(user_id: int) -> dict[int, int]:
        return {
            ups.setting: ups.scope
            for ups in UserPrivacySetting.objects.filter(user_id=user_id)
        }

    @staticmethod
    def check_privacy(
        user_id: int,
        viewer_id: int | None,
        setting: PrivacySetting,
        scope_map: dict[int, int] | None = None,
    ) -> bool:
        if user_id == viewer_id:
            return True

        from main.social.services import BlockService, FollowService

        if viewer_id and BlockService.is_blocked(user_id, viewer_id):
            return False

        if scope_map is None:
            ups = UserPrivacySetting.objects.filter(
                user_id=user_id, setting=setting
            ).first()
            scope = (
                ups.scope
                if ups
                else DEFAULT_PRIVACY_SCOPES.get(setting, PrivacyScope.NOONE)
            )
        else:
            scope = scope_map.get(
                setting, DEFAULT_PRIVACY_SCOPES.get(setting, PrivacyScope.NOONE)
            )

        if scope == PrivacyScope.EVERYONE:
            return True
        if scope == PrivacyScope.NOONE:
            return False
        if not viewer_id:  # anonymous viewer cannot be a follower or mutual
            return False
        if scope == PrivacyScope.FOLLOWERS:
            return FollowService.is_following(viewer_id, user_id)
        if scope == PrivacyScope.MUTUALS:
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
        UserPrivacySetting.objects.bulk_create(
            [
                UserPrivacySetting(
                    user_id=user_id,
                    setting=setting.value,
                    scope=DEFAULT_PRIVACY_SCOPES.get(setting, PrivacyScope.NOONE),
                )
                for setting in PrivacySetting
            ],
            ignore_conflicts=True,
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
    def get_or_create_preferences(user: User) -> UserPreferences:
        preferences, _ = UserPreferences.objects.get_or_create(user=user)
        return preferences

    @staticmethod
    def alter_preferences(
        user: User,
        preferred_activities: list[dict] | None = None,
        availabilities: list[dict] | None = None,
        participation_groups: list[int] | None = None,
        **fields,
    ) -> UserPreferences:
        validate_preferences(fields)

        with transaction.atomic():
            preferences = UserService.get_or_create_preferences(user)
            for field, value in fields.items():
                if value is not None:
                    setattr(preferences, field, value)
            preferences.save()

            # multi-valued answers use full-replace semantics when provided
            if preferred_activities is not None:
                UserPreferredActivity.objects.filter(preferences=preferences).delete()
                UserPreferredActivity.objects.bulk_create(
                    [
                        UserPreferredActivity(
                            preferences=preferences,
                            activity_id=item["activity"],
                            skill_level=item["skill_level"],
                        )
                        for item in preferred_activities
                    ],
                    ignore_conflicts=True,
                )

            if availabilities is not None:
                UserAvailability.objects.filter(preferences=preferences).delete()
                UserAvailability.objects.bulk_create(
                    [
                        UserAvailability(
                            preferences=preferences,
                            day_of_week=slot["day_of_week"],
                            time_of_day=slot["time_of_day"],
                        )
                        for slot in availabilities
                    ],
                    ignore_conflicts=True,
                )

            if participation_groups is not None:
                UserParticipationGroup.objects.filter(
                    preferences=preferences
                ).delete()
                UserParticipationGroup.objects.bulk_create(
                    [
                        UserParticipationGroup(
                            preferences=preferences, group_kind=kind
                        )
                        for kind in participation_groups
                    ],
                    ignore_conflicts=True,
                )

        return preferences

    @staticmethod
    def alter_max_travel_distance(user: User, distance: int = None) -> UserPreferences:
        validate_max_travel_distance(distance)
        preferences = UserService.get_or_create_preferences(user)
        preferences.max_travel_distance = distance
        preferences.save()
        return preferences

    @staticmethod
    def alter_all_privacy_settings(user_id: int, scope: PrivacyScope) -> None:
        UserPrivacySetting.objects.filter(user_id=user_id).update(scope=scope)

    @staticmethod
    def alter_privacy_setting(
        user_id: int, setting: PrivacySetting, scope: PrivacyScope
    ) -> UserPrivacySetting:
        ups, _ = UserPrivacySetting.objects.update_or_create(
            user_id=user_id, setting=setting, defaults={"scope": scope}
        )
        return ups

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
