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
)
from ..error import MUError, MUErrorCode


class BasicInfoMutation(graphene.Mutation):

    class Arguments:
        date_of_birth = graphene.Date(required = False)
        first_name = graphene.String(required = False)
        last_name = graphene.String(required = False)
        bio = graphene.String(required = False)
        gender = Gender.as_graphene_enum()(required=False)

    success = graphene.Boolean()

    @require_auth
    def mutate(
        cls,
        root,
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

        return BasicInfoMutation(success = True)

class SubmitSurveyMutation(graphene.Mutation):

    class Arguments:
        frequency_of_physical_activity = FrequencyOfPhycicalActivity.as_graphene_enum()(required=True)
        social_interaction_importance = SocialInteractionImportance.as_graphene_enum()(required=True)
        preferred_party_size = PreferredPartySize.as_graphene_enum()(required=True)
        physical_activity_satisfaction = PhysicalActivitySatisfaction.as_graphene_enum()(required=True)
        matched_participation_likelihood = MatchedParticipationLikelihood.as_graphene_enum()(required=True)
        main_interest = MainInterest.as_graphene_enum()(required=True)
        preferred_event_duration = graphene.Int(required=True)
        formed_relationship_types = graphene.List(
            FormedRelationshipsType.as_graphene_enum(),
            required=True
        )
        preferred_partner_characteristics = graphene.List(
            PreferredPartnerCharacteristics.as_graphene_enum(),
            required=True
        )
        preferred_time_of_the_day = graphene.List(
            TimeOfTheDay.as_graphene_enum(),
            required=True
        )
        gender_preference = graphene.List(
            Gender.as_graphene_enum(),
            required=True
        )

    success = graphene.Boolean()

    @require_auth
    def mutate(
        cls, 
        root, 
        info,
        frequency_of_physical_activity: FrequencyOfPhycicalActivity,
        social_interaction_importance: SocialInteractionImportance,
        preferred_party_size: PreferredPartySize,
        physical_activity_satisfaction: PhysicalActivitySatisfaction,
        matched_participation_likelihood: MatchedParticipationLikelihood,
        main_interest: MainInterest,
        preferred_event_duration: int,
        formed_relationship_types: list = [],
        preferred_partner_characteristics: list = [],
        preferred_time_of_the_day: list = [],
        gender_preference: list = [],
        **kwargs
        ):

        if Gender.PREFER_NOT_TO_SAY in gender_preference:
            raise MUError(MUErrorCode.USER_PREFERRED_GENDERS_CHOICE)

        if not 1 <= preferred_event_duration <= 200:
            raise MUError(MUErrorCode.PREFERRED_EVENT_DURATION_RANGE)

        user: User = info.context.user

        user.frequency_of_physical_activity = frequency_of_physical_activity
        user.social_interaction_importance = social_interaction_importance
        user.preferred_party_size = preferred_party_size
        user.physical_activity_satisfaction = physical_activity_satisfaction
        user.matched_participation_likelihood = matched_participation_likelihood
        user.main_interest = main_interest
        user.preferred_event_duration = preferred_event_duration
        user.formed_relationship_types = formed_relationship_types
        user.preferred_partner_characteristics = preferred_partner_characteristics
        user.preferred_time_of_the_day = preferred_time_of_the_day
        user.gender_preference = gender_preference

        user.save()

        return SubmitSurveyMutation(success = True)

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
    submit_survey = SubmitSurveyMutation.Field()
    submit_basic_info = BasicInfoMutation.Field()
    update_max_travel_distance = UpdateMaxTravelDistanceMutation.Field()
