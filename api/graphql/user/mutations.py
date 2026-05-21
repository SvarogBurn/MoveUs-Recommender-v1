import graphene

from api.graphql.user.types import PrivacySettingType, ProfileType
from main.user.models import User
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
    PrivacyScope,
    PrivacySetting,
    SocialInteractionImportance,
    TimeOfTheDay,
)
from shared.utils.decorators import require_auth


class AlterBasicInfoMutation(graphene.Mutation):

    class Arguments:
        date_of_birth = graphene.Date(required=False)
        first_name = graphene.String(required=False)
        last_name = graphene.String(required=False)
        bio = graphene.String(required=False)
        gender = Gender.as_graphene_enum()(required=False)

    my_profile = graphene.Field(ProfileType)

    @require_auth
    def mutate(
        self,
        info: graphene.ResolveInfo,
        date_of_birth=None,
        first_name: str | None = None,
        last_name: str | None = None,
        bio: str | None = None,
        gender=None,
    ):

        user: User = info.context.user

        fields = {}
        if first_name is not None:
            fields["first_name"] = first_name
        if last_name is not None:
            fields["last_name"] = last_name
        if date_of_birth:
            fields["date_of_birth"] = date_of_birth
        if bio is not None:
            fields["bio"] = bio
        if gender is not None:
            fields["gender"] = gender

        UserService.alter_basic_info(user, **fields)

        return AlterBasicInfoMutation(my_profile=user)


class AlterSurveyInfoMutation(graphene.Mutation):

    class Arguments:
        frequency_of_physical_activity = FrequencyOfPhycicalActivity.as_graphene_enum()(
            required=False
        )
        social_interaction_importance = SocialInteractionImportance.as_graphene_enum()(
            required=False
        )
        preferred_party_size = PreferredPartySize.as_graphene_enum()(required=False)
        physical_activity_satisfaction = (
            PhysicalActivitySatisfaction.as_graphene_enum()(required=False)
        )
        matched_participation_likelihood = (
            MatchedParticipationLikelihood.as_graphene_enum()(required=False)
        )
        main_interest = MainInterest.as_graphene_enum()(required=False)
        preferred_event_duration = graphene.Int(required=False)
        formed_relationship_kinds = graphene.List(
            FormedRelationshipsKind.as_graphene_enum(), required=False
        )
        preferred_partner_characteristics = graphene.List(
            PreferredPartnerCharacteristics.as_graphene_enum(), required=False
        )
        preferred_time_of_the_day = graphene.List(
            TimeOfTheDay.as_graphene_enum(), required=False
        )
        gender_preference = graphene.List(
            GenderNoPNTS.as_graphene_enum(), required=False
        )

    my_profile = graphene.Field(ProfileType)

    @require_auth
    def mutate(
        self,
        info: graphene.ResolveInfo,
        frequency_of_physical_activity: FrequencyOfPhycicalActivity = None,
        social_interaction_importance: SocialInteractionImportance = None,
        preferred_party_size: PreferredPartySize = None,
        physical_activity_satisfaction: PhysicalActivitySatisfaction = None,
        matched_participation_likelihood: MatchedParticipationLikelihood = None,
        main_interest: MainInterest = None,
        preferred_event_duration: int = None,
        formed_relationship_kinds: list = [],
        preferred_partner_characteristics: list = [],
        preferred_time_of_the_day: list = [],
        gender_preference: list = [],
        **kwargs
    ):

        user: User = info.context.user

        fields = {}
        if frequency_of_physical_activity is not None:
            fields["frequency_of_physical_activity"] = frequency_of_physical_activity
        if social_interaction_importance is not None:
            fields["social_interaction_importance"] = social_interaction_importance
        if preferred_party_size is not None:
            fields["preferred_party_size"] = preferred_party_size
        if physical_activity_satisfaction is not None:
            fields["physical_activity_satisfaction"] = physical_activity_satisfaction
        if matched_participation_likelihood is not None:
            fields["matched_participation_likelihood"] = matched_participation_likelihood
        if main_interest is not None:
            fields["main_interest"] = main_interest
        if preferred_event_duration is not None:
            fields["preferred_event_duration"] = preferred_event_duration

        UserService.alter_survey_info(
            user,
            formed_relationship_kinds=formed_relationship_kinds,
            preferred_partner_characteristics=preferred_partner_characteristics,
            preferred_time_of_the_day=preferred_time_of_the_day,
            gender_preference=gender_preference,
            **fields,
        )

        return AlterSurveyInfoMutation(my_profile=user)


class AlterMaxTravelDistanceMutation(graphene.Mutation):

    class Arguments:
        distance = graphene.Int(required=False)

    my_profile = graphene.Field(ProfileType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, distance: int = None):
        user: User = info.context.user
        UserService.alter_max_travel_distance(user, distance)
        return AlterMaxTravelDistanceMutation(my_profile=user)


class AlterAllPrivacySettingsMutation(graphene.Mutation):

    class Arguments:
        scope = PrivacyScope.as_graphene_enum()(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, scope: PrivacyScope):

        UserService.alter_all_privacy_settings(info.context.user.id, scope)

        return AlterAllPrivacySettingsMutation(success=True)


class AlterPrivacySettingMutation(graphene.Mutation):

    class Arguments:
        setting = PrivacySetting.as_graphene_enum()(required=True)
        scope = PrivacyScope.as_graphene_enum()(required=True)

    privacy_setting = graphene.Field(PrivacySettingType)

    @require_auth
    def mutate(
        self,
        info: graphene.ResolveInfo,
        setting: PrivacySetting,
        scope: PrivacyScope,
    ):
        ups = UserService.alter_privacy_setting(
            info.context.user.id, setting, scope
        )
        return AlterPrivacySettingMutation(privacy_setting=ups)


class Mutation(graphene.ObjectType):
    alter_survey_info = AlterSurveyInfoMutation.Field()
    alter_basic_info = AlterBasicInfoMutation.Field()
    alter_max_travel_distance = AlterMaxTravelDistanceMutation.Field()
    alter_all_privacy_settings = AlterAllPrivacySettingsMutation.Field()
    alter_privacy_setting = AlterPrivacySettingMutation.Field()
