import graphene

from api.graphql.event.types import EventType
from main.event.services import EventService
from main.social.services import FollowService, PostService
from main.user.models import User, UserPrivacySetting
from main.user.services import UserService
from shared.enums import (
    FormedRelationshipsKind,
    FrequencyOfPhycicalActivity,
    Gender,
    GenderNoPNTS,
    MainInterest,
    MatchedParticipationLikelihood,
    PhysicalActivitySatisfaction,
    PreferredPartnerCharacteristics,
    PreferredPartySize,
    PrivacySetting,
    SocialInteractionImportance,
    TimeOfTheDay,
)

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

    def resolve_followers(self, info: graphene.ResolveInfo) -> list[User] | None:
        if not UserService.check_privacy(
            self.id, info.context.user.id, PrivacySetting.FOLLOWERS
        ):
            return None
        return FollowService.get_follower_users(self.id)

    def resolve_follower_count(self: User, info: graphene.ResolveInfo) -> int | None:
        if not UserService.check_privacy(
            self.id, info.context.user.id, PrivacySetting.FOLLOWERS
        ):
            return None
        return FollowService.get_follower_count(self.id)

    def resolve_following(self, info: graphene.ResolveInfo) -> list[User] | None:
        if not UserService.check_privacy(
            self.id, info.context.user.id, PrivacySetting.FOLLOWERS
        ):
            return None
        return FollowService.get_following_users(self.id)

    def resolve_following_count(self: User, info: graphene.ResolveInfo) -> int | None:
        if not UserService.check_privacy(
            self.id, info.context.user.id, PrivacySetting.FOLLOWERS
        ):
            return None
        return FollowService.get_following_count(self.id)

    def resolve_organizing_events(self: User, info: graphene.ResolveInfo):
        return EventService.get_organizing_events(self.id)

    def resolve_attending_events(self: User, info: graphene.ResolveInfo):
        return EventService.get_attending_events(self.id)

    def resolve_posts(self: User, info: graphene.ResolveInfo, start: int, end: int):
        return PostService.get_user_posts(self.id, start, end)


class ProfileType(MUObjectType, UserTypeMixin):

    formed_relationship_kinds = graphene.List(
        FormedRelationshipsKind.as_graphene_enum()
    )
    preferred_partner_characteristics = graphene.List(
        PreferredPartnerCharacteristics.as_graphene_enum()
    )
    preferred_time_of_the_day = graphene.List(TimeOfTheDay.as_graphene_enum())
    gender_preference = graphene.List(GenderNoPNTS.as_graphene_enum())

    frequency_of_physical_activity = FrequencyOfPhycicalActivity.as_graphene_enum()()
    social_interaction_importance = SocialInteractionImportance.as_graphene_enum()()
    preferred_party_size = PreferredPartySize.as_graphene_enum()()
    physical_activity_satisfaction = PhysicalActivitySatisfaction.as_graphene_enum()()
    matched_participation_likelihood = (
        MatchedParticipationLikelihood.as_graphene_enum()()
    )
    main_interest = MainInterest.as_graphene_enum()()

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

    def resolve_formed_relationship_kinds(
        self: User, info: graphene.ResolveInfo
    ) -> list[str]:
        if self.formed_relationship_kinds is None:
            return []
        frt_formatted = [
            next(n for n, v in vars(FormedRelationshipsKind).items() if v == x)
            for x in self.formed_relationship_kinds
        ]
        return frt_formatted

    def resolve_preferred_partner_characteristics(
        self: User, info: graphene.ResolveInfo
    ) -> list[str]:
        if self.preferred_partner_characteristics is None:
            return []
        ppc_formatted = [
            next(n for n, v in vars(PreferredPartnerCharacteristics).items() if v == x)
            for x in self.preferred_partner_characteristics
        ]
        return ppc_formatted

    def resolve_preferred_time_of_the_day(
        self: User, info: graphene.ResolveInfo
    ) -> list[str]:
        if self.preferred_time_of_the_day is None:
            return []
        ptd_formatted = [
            next(n for n, v in vars(TimeOfTheDay).items() if v == x)
            for x in self.preferred_time_of_the_day
        ]
        return ptd_formatted

    def resolve_gender_preference(
        self: User, info: graphene.ResolveInfo
    ) -> list[str]:
        if self.gender_preference is None:
            return []
        gpf_formatted = [
            next(n for n, v in vars(GenderNoPNTS).items() if v == x)
            for x in self.gender_preference
        ]
        return gpf_formatted

    def resolve_frequency_of_physical_activity(
        self: User, info: graphene.ResolveInfo
    ) -> int | None:
        return self.frequency_of_physical_activity

    def resolve_social_interaction_importance(
        self: User, info: graphene.ResolveInfo
    ) -> int | None:
        return self.social_interaction_importance

    def resolve_preferred_party_size(
        self: User, info: graphene.ResolveInfo
    ) -> int | None:
        return self.preferred_party_size

    def resolve_physical_activity_satisfaction(
        self: User, info: graphene.ResolveInfo
    ) -> int | None:
        return self.physical_activity_satisfaction

    def resolve_matched_participation_likelihood(
        self: User, info: graphene.ResolveInfo
    ) -> int | None:
        return self.matched_participation_likelihood

    def resolve_main_interest(
        self: User, info: graphene.ResolveInfo
    ) -> int | None:
        return self.main_interest


class UserType(MUObjectType, UserTypeMixin):
    location = graphene.Field(LocationType)
    email = graphene.String()
    date_of_birth = graphene.Date()
    gender = Gender.as_graphene_enum()()
    is_following = graphene.Boolean()
    is_followed_by = graphene.Boolean()

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
            "preferred_activities",
        )

    def resolve_location(self: User, info: graphene.ResolveInfo):
        if UserService.check_privacy(self.id, info.context.user.id, PrivacySetting.LOCATION):
            return self.location

    def resolve_email(self: User, info: graphene.ResolveInfo) -> str | None:
        if UserService.check_privacy(self.id, info.context.user.id, PrivacySetting.EMAIL):
            return self.email

    def resolve_date_of_birth(self: User, info: graphene.ResolveInfo):
        if UserService.check_privacy(self.id, info.context.user.id, PrivacySetting.AGE):
            return self.date_of_birth

    def resolve_gender(self: User, info: graphene.ResolveInfo) -> int | None:
        if UserService.check_privacy(self.id, info.context.user.id, PrivacySetting.GENDER):
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

    class Meta:
        model = UserPrivacySetting
        fields = ("setting", "scope")
        convert_choices_to_enum = False
