import graphene

from main_app.util import require_auth
from main_app.validators import profile_validator

from ...models import User
from ...models.enums import (
    FormedRelationshipsType,
    FrequencyOfPhycicalActivity,
    Gender,
    MainInterest,
    MatchedParticipationLikelihood,
    PhysicalActivitySatisfaction,
    PreferredPartnerCharacteristics,
    PreferredPartySize,
    SocialInteractionImportance,
    TimeOfTheDay,
    GenderNoPNTS
)
from ..error import MUError, MUErrorCode


class UpdateBasicInfoMutation(graphene.Mutation):

    class Arguments:
        date_of_birth = graphene.Date(required = False)
        first_name = graphene.String(required = False)
        last_name = graphene.String(required = False)
        bio = graphene.String(required = False)
        gender = Gender.as_graphene_enum()(required=False)

    success = graphene.Boolean()

    @require_auth
    def mutate(
        self,
        info,
        date_of_birth = None,
        first_name = None,
        last_name = None,
        bio = None,
        gender = None
    ):
        
        user: User = info.context.user

        profile_validator(first_name, last_name, date_of_birth, bio)

        if first_name is not None: user.first_name = first_name
        if last_name is not None: user.last_name = last_name
        if date_of_birth: user.date_of_birth = date_of_birth
        if bio is not None: user.bio = bio
        if gender is not None: user.gender = gender

        user.save()

        return UpdateBasicInfoMutation(success = True)

class UpdateSurveyInfoMutation(graphene.Mutation):

    class Arguments:
        frequency_of_physical_activity = FrequencyOfPhycicalActivity.as_graphene_enum()(required=False)
        social_interaction_importance = SocialInteractionImportance.as_graphene_enum()(required=False)
        preferred_party_size = PreferredPartySize.as_graphene_enum()(required=False)
        physical_activity_satisfaction = PhysicalActivitySatisfaction.as_graphene_enum()(required=False)
        matched_participation_likelihood = MatchedParticipationLikelihood.as_graphene_enum()(required=False)
        main_interest = MainInterest.as_graphene_enum()(required=False)
        preferred_event_duration = graphene.Int(required=False)
        formed_relationship_types = graphene.List(
            FormedRelationshipsType.as_graphene_enum(),
            required=False
        )
        preferred_partner_characteristics = graphene.List(
            PreferredPartnerCharacteristics.as_graphene_enum(),
            required=False
        )
        preferred_time_of_the_day = graphene.List(
            TimeOfTheDay.as_graphene_enum(),
            required=False
        )
        gender_preference = graphene.List(
            GenderNoPNTS.as_graphene_enum(),
            required=False
        )

    success = graphene.Boolean()

    @require_auth
    def mutate(
        self, 
        info,
        frequency_of_physical_activity: FrequencyOfPhycicalActivity = None,
        social_interaction_importance: SocialInteractionImportance = None,
        preferred_party_size: PreferredPartySize = None,
        physical_activity_satisfaction: PhysicalActivitySatisfaction = None,
        matched_participation_likelihood: MatchedParticipationLikelihood = None,
        main_interest: MainInterest = None,
        preferred_event_duration: int = None,
        formed_relationship_types: list = [],
        preferred_partner_characteristics: list = [],
        preferred_time_of_the_day: list = [],
        gender_preference: list = [],
        **kwargs
        ):

        if preferred_event_duration and not 1 <= preferred_event_duration <= 200:
            raise MUError(MUErrorCode.PREFERRED_EVENT_DURATION_RANGE)

        user: User = info.context.user

        if frequency_of_physical_activity is not None: user.frequency_of_physical_activity = frequency_of_physical_activity
        if social_interaction_importance is not None: user.social_interaction_importance = social_interaction_importance
        if preferred_party_size is not None: user.preferred_party_size = preferred_party_size
        if physical_activity_satisfaction is not None: user.physical_activity_satisfaction = physical_activity_satisfaction
        if matched_participation_likelihood is not None: user.matched_participation_likelihood = matched_participation_likelihood
        if main_interest is not None: user.main_interest = main_interest
        if preferred_event_duration is not None: user.preferred_event_duration = preferred_event_duration
        user.formed_relationship_types = formed_relationship_types
        user.preferred_partner_characteristics = preferred_partner_characteristics
        user.preferred_time_of_the_day = preferred_time_of_the_day
        user.gender_preference = gender_preference

        user.save()

        return UpdateBasicInfoMutation(success = True)

class UpdateMaxTravelDistanceMutation(graphene.Mutation):

    class Arguments:
        distance = graphene.Int(required = False)

    success = graphene.Boolean()

    @require_auth
    def mutate(self, info, distance: int = None):
        user: User = info.context.user
        if distance is not None and not 1 <= distance < 2e5:
            raise MUError(MUErrorCode.TRAVEL_DISTANCE_RANGE)
        user.max_travel_distance = distance
        return UpdateMaxTravelDistanceMutation(success = True)

class Mutation(graphene.ObjectType):
    update_survey_info = UpdateSurveyInfoMutation.Field()
    update_basic_info = UpdateBasicInfoMutation.Field()
    update_max_travel_distance = UpdateMaxTravelDistanceMutation.Field()
