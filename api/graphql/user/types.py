import graphene

from api.graphql.event.types import EventType
from main.event.services import EventService
from main.location.models import Location
from main.social.services import FollowService, PostService
from main.user.decorators import owner_only, privacy_gated
from main.user.models import (
    User,
    UserAvailability,
    UserPreferences,
    UserPreferredActivity,
    UserPrivacySetting,
)
from main.user.services import UserService
from shared.enums import (
    AcquaintancePreference,
    DayOfWeek,
    Gender,
    OrganizingOpenness,
    ParticipationGroupKind,
    PrivacyScope,
    PrivacySetting,
    TimeOfTheDay,
)

from ..activity.types import PreferredActivityType
from ..location.types import LocationType
from ..object_type import MUObjectType


class UserTypeMixin:
    likes = graphene.Int()
    dislikes = graphene.Int()
    followers = graphene.List(lambda: UserType)
    follower_count = graphene.Int()
    following = graphene.List(lambda: UserType)
    following_count = graphene.Int()
    organizing_events = graphene.List(EventType)
    attending_events = graphene.List(EventType)
    posts = graphene.List(
        graphene.lazy_import("api.graphql.social.types.PostType"),
        start=graphene.Int(default_value=0),
        end=graphene.Int(default_value=10),
    )

    def resolve_likes(self: User, info: graphene.ResolveInfo) -> int:
        return UserService.get_event_likes_count(self.id)

    def resolve_dislikes(self: User, info: graphene.ResolveInfo) -> int:
        return UserService.get_event_dislikes_count(self.id)

    @privacy_gated(PrivacySetting.FOLLOWERS)
    def resolve_followers(self, info: graphene.ResolveInfo) -> list[User] | None:
        return FollowService.get_follower_users(self.id)

    @privacy_gated(PrivacySetting.FOLLOWERS)
    def resolve_follower_count(self: User, info: graphene.ResolveInfo) -> int | None:
        return FollowService.get_follower_count(self.id)

    @privacy_gated(PrivacySetting.FOLLOWERS)
    def resolve_following(self, info: graphene.ResolveInfo) -> list[User] | None:
        return FollowService.get_following_users(self.id)

    @privacy_gated(PrivacySetting.FOLLOWERS)
    def resolve_following_count(self: User, info: graphene.ResolveInfo) -> int | None:
        return FollowService.get_following_count(self.id)

    def resolve_organizing_events(self: User, info: graphene.ResolveInfo):
        return EventService.get_organizing_events(self.id)

    def resolve_attending_events(self: User, info: graphene.ResolveInfo):
        return EventService.get_attending_events(self.id)

    @privacy_gated(PrivacySetting.POSTS)
    def resolve_posts(self: User, info: graphene.ResolveInfo, start: int, end: int):
        viewer_id = info.context.user.id or None
        return PostService.get_user_posts(self.id, start, end, viewer_id=viewer_id)


class UserAvailabilityType(MUObjectType):
    day_of_week = DayOfWeek.as_graphene_enum()()
    time_of_day = TimeOfTheDay.as_graphene_enum()()

    class Meta:
        model = UserAvailability
        fields = ("day_of_week", "time_of_day")
        convert_choices_to_enum = False

    def resolve_day_of_week(self: UserAvailability, info: graphene.ResolveInfo) -> int:
        return self.day_of_week

    def resolve_time_of_day(self: UserAvailability, info: graphene.ResolveInfo) -> int:
        return self.time_of_day


class UserPreferencesType(MUObjectType):
    organizing_openness = OrganizingOpenness.as_graphene_enum()()
    acquaintance_preference = AcquaintancePreference.as_graphene_enum()()
    availabilities = graphene.List(UserAvailabilityType)
    participation_groups = graphene.List(ParticipationGroupKind.as_graphene_enum())

    class Meta:
        model = UserPreferences
        exclude = ("user",)
        convert_choices_to_enum = True

    def resolve_organizing_openness(
        self: UserPreferences, info: graphene.ResolveInfo
    ) -> int | None:
        return self.organizing_openness

    def resolve_acquaintance_preference(
        self: UserPreferences, info: graphene.ResolveInfo
    ) -> int | None:
        return self.acquaintance_preference

    def resolve_availabilities(
        self: UserPreferences, info: graphene.ResolveInfo
    ) -> list[UserAvailability]:
        return list(self.availabilities.all())

    def resolve_participation_groups(
        self: UserPreferences, info: graphene.ResolveInfo
    ) -> list[str]:
        return [
            ParticipationGroupKind(pg.group_kind).name
            for pg in self.participation_groups.all()
        ]


class ProfileType(MUObjectType, UserTypeMixin):

    preferences = graphene.Field(UserPreferencesType)
    preferred_activities = graphene.List(PreferredActivityType)

    class Meta:
        model = User
        exclude = (
            "is_superuser",
            "is_staff",
            "authored_posts",
            "comment_set",
            "following_set",
            "followers_set",
            "blocking_set",
            "blocked_by_set",
            "direct_chats_as_user_1",
            "direct_chats_as_user_2",
        )
        convert_choices_to_enum = True

    def resolve_preferences(
        self: User, info: graphene.ResolveInfo
    ) -> UserPreferences:
        return UserService.get_or_create_preferences(self)

    def resolve_preferred_activities(
        self: User, info: graphene.ResolveInfo
    ) -> list[UserPreferredActivity]:
        return list(
            UserPreferredActivity.objects.filter(preferences__user=self)
        )


class UserType(MUObjectType, UserTypeMixin):
    location = graphene.Field(LocationType)
    email = graphene.String()
    date_of_birth = graphene.Date()
    gender = Gender.as_graphene_enum()()
    is_following = graphene.Boolean()
    is_followed_by = graphene.Boolean()
    preferred_activities = graphene.List(PreferredActivityType)

    class Meta:
        model = User
        fields = (
            "id",
            "bio",
            "first_name",
            "last_name",
            "xp",
            "verified",
            "gender",
            "username",
            "is_active",
            "date_joined",
        )

    def resolve_preferred_activities(
        self: User, info: graphene.ResolveInfo
    ) -> list[UserPreferredActivity]:
        return list(
            UserPreferredActivity.objects.filter(preferences__user=self)
        )

    @privacy_gated(PrivacySetting.LOCATION)
    def resolve_location(self: User, info: graphene.ResolveInfo):
        if self.longitude is None or self.latitude is None:
            return None
        return Location(longitude=self.longitude, latitude=self.latitude)

    @owner_only
    def resolve_email(self: User, info: graphene.ResolveInfo) -> str | None:
        return self.email

    @privacy_gated(PrivacySetting.AGE)
    def resolve_date_of_birth(self: User, info: graphene.ResolveInfo):
        return self.date_of_birth

    @privacy_gated(PrivacySetting.GENDER)
    def resolve_gender(self: User, info: graphene.ResolveInfo) -> int | None:
        return self.gender

    def resolve_is_following(self: User, info: graphene.ResolveInfo) -> bool | None:
        viewer = info.context.user
        if not viewer or viewer.is_anonymous:
            return None
        return FollowService.is_following(viewer.id, self.id)

    def resolve_is_followed_by(self: User, info: graphene.ResolveInfo) -> bool | None:
        viewer = info.context.user
        if not viewer or viewer.is_anonymous:
            return None
        return FollowService.is_following(self.id, viewer.id)


class PrivacySettingType(MUObjectType):
    setting = PrivacySetting.as_graphene_enum()()
    scope = PrivacyScope.as_graphene_enum()()

    class Meta:
        model = UserPrivacySetting
        fields = ("setting", "scope")
        convert_choices_to_enum = False

    def resolve_setting(self: UserPrivacySetting, info: graphene.ResolveInfo) -> int:
        return self.setting

    def resolve_scope(self: UserPrivacySetting, info: graphene.ResolveInfo) -> int:
        return self.scope
