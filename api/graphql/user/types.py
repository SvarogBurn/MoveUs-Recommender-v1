import json

import graphene
from django.db.models import Q

from api.graphql.event.types import EventType
from api.graphql.social.types import RelationshipType
from main.event.models import Event, EventMember, EventMemberLike
from main.social.models import Relationship
from main.user.models import User, UserPrivacySetting
from shared.enums import (
    FormedRelationshipsType,
    FrequencyOfPhycicalActivity,
    Gender,
    GenderNoPNTS,
    MainInterest,
    MatchedParticipationLikelihood,
    MemberRole,
    PhysicalActivitySatisfaction,
    PreferredPartnerCharacteristics,
    PreferredPartySize,
    PrivacyScope,
    PrivacySetting,
    RelationshipStatus,
    SocialInteractionImportance,
    TimeOfTheDay,
)

from ..location.types import LocationType
from ..object_type import MUObjectType


def _check_privacy(user: User, viewer: User, setting: PrivacySetting) -> bool:
    """Return True if the viewer is allowed to see this field."""
    if user.id == viewer.id:
        return True
    ups = UserPrivacySetting.objects.filter(user=user, setting=setting).first()
    if not ups or ups.scope == PrivacyScope.EVERYONE:
        return True
    if ups.scope == PrivacyScope.FRIENDS:
        rel = _get_viewer_relationship(user, viewer)
        return rel is not None and rel.status == RelationshipStatus.FRIENDS
    return False


def _get_viewer_relationship(user: User, viewer: User) -> Relationship | None:
    """Get and cache the relationship between user and viewer."""
    cache_attr = f"_rel_cache_{viewer.id}"
    if hasattr(user, cache_attr):
        return getattr(user, cache_attr)
    q1 = Q(user_1=user, user_2=viewer)
    q2 = Q(user_2=user, user_1=viewer)
    rel = Relationship.objects.filter(q1 | q2).first()
    setattr(user, cache_attr, rel)
    return rel


class UserTypeMixin:
    likes = graphene.Int()
    dislikes = graphene.Int()
    friends = graphene.List(lambda: UserType)
    friend_count = graphene.Int()
    organizing_events = graphene.List(EventType)
    attending_events = graphene.List(EventType)
    posts = graphene.List(
        graphene.lazy_import("api.graphql.social.types.PostType"),
        start=graphene.Int(default_value=0),
        end=graphene.Int(default_value=10),
    )

    def resolve_likes(self: User, info: graphene.ResolveInfo) -> int:
        return EventMemberLike.objects.filter(user_2=self, like=True).count()

    def resolve_dislikes(self: User, info: graphene.ResolveInfo) -> int:
        return EventMemberLike.objects.filter(user_2=self, like=False).count()

    def resolve_friends(self, info: graphene.ResolveInfo) -> list[User] | None:
        if not _check_privacy(self, info.context.user, PrivacySetting.FRIENDS):
            return None

        user1_q = Q(user_1=self)
        user2_q = Q(user_2=self)
        rels = Relationship.objects.filter(
            user1_q | user2_q, status=RelationshipStatus.FRIENDS
        )
        return [r.user_1 if self.id == r.user_2.id else r.user_2 for r in rels]

    def resolve_friend_count(self: User, info: graphene.ResolveInfo) -> int | None:
        if not _check_privacy(self, info.context.user, PrivacySetting.FRIENDS):
            return None

        user1_q = Q(user_1=self)
        user2_q = Q(user_2=self)
        return Relationship.objects.filter(
            user1_q | user2_q, status=RelationshipStatus.FRIENDS
        ).count()

    def resolve_organizing_events(self: User, info: graphene.ResolveInfo):
        return Event.objects.filter(
            id__in=EventMember.objects.filter(
                user=self, role=MemberRole.ORGANIZER
            ).values("event_id")
        )

    def resolve_attending_events(self: User, info: graphene.ResolveInfo):
        return Event.objects.filter(
            id__in=EventMember.objects.filter(
                user=self,
                role__in=[
                    MemberRole.PARTICIPANT,
                    MemberRole.MODERATOR,
                    MemberRole.SPECTATOR,
                ],
            ).values("event_id")
        )

    def resolve_posts(self: User, info: graphene.ResolveInfo, start: int, end: int):
        return self.authored_posts.select_related("author").order_by("-time_posted")[
            start:end
        ]


class ProfileType(MUObjectType, UserTypeMixin):

    formed_relationship_types = graphene.List(
        FormedRelationshipsType.as_graphene_enum()
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
            "postcomment_set",
            "friends_added",
            "friends_added_by",
        )
        convert_choices_to_enum = True

    def resolve_formed_relationship_types(
        self: User, info: graphene.ResolveInfo
    ) -> list[str]:
        if self.formed_relationship_types is None:
            return []
        frt_formatted = [
            next(n for n, v in vars(FormedRelationshipsType).items() if v == x)
            for x in self.formed_relationship_types
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
    relationship = graphene.Field(RelationshipType)

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
        if _check_privacy(self, info.context.user, PrivacySetting.LOCATION):
            return self.location

    def resolve_email(self: User, info: graphene.ResolveInfo) -> str | None:
        if _check_privacy(self, info.context.user, PrivacySetting.EMAIL):
            return self.email

    def resolve_date_of_birth(self: User, info: graphene.ResolveInfo):
        if _check_privacy(self, info.context.user, PrivacySetting.AGE):
            return self.date_of_birth

    def resolve_gender(self: User, info: graphene.ResolveInfo) -> int | None:
        if _check_privacy(self, info.context.user, PrivacySetting.GENDER):
            return self.gender

    def resolve_relationship(
        self: User, info: graphene.ResolveInfo
    ) -> Relationship | None:
        if not info.context.user or info.context.user.is_anonymous:
            return None
        return _get_viewer_relationship(self, info.context.user)


class PrivacySettingType(MUObjectType):

    class Meta:
        model = UserPrivacySetting
        fields = ("setting", "scope")
        convert_choices_to_enum = False
