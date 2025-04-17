import graphene

from main_app.graphql.user.types import ProfileType
from main_app.validators import profile_validator

from ...models.enums import Gender, TimeOfTheDay
from ..error import MUError, MUErrorCode
from ...models import User
from ...models.enums import (
    FrequencyOfPhycicalActivity,
    SocialInteractionImportance,
    PreferredPartySize,
    FormedRelationshipsType,
    PhysicalActivitySatisfaction,
    PreferredPartnerCharacteristics,
    MatchedParticipationLikelihood
)

class BasicInfoMutation(graphene.Mutation):

    class Arguments:
        date_of_birth = graphene.Date(required = False)
        first_name = graphene.String(required = False)
        last_name = graphene.String(required = False)
        bio = graphene.String(required = False)
        gender = Gender.as_graphene_enum()(required=False)

    my_profile = graphene.Field(ProfileType)

    @classmethod
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
        if not user.id: raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)

        profile_validator(first_name, last_name, date_of_birth, bio)

        if first_name is not None: user.first_name = first_name
        if last_name is not None: user.last_name = last_name
        if date_of_birth: user.date_of_birth = date_of_birth
        if bio is not None: user.bio = bio
        if gender is not None: user.gender = gender

        user.save()

        return BasicInfoMutation(my_profile = user)

class SubmitSurveyMutation(graphene.Mutation):

    class Arguments:
        frequency_of_physical_activity = FrequencyOfPhycicalActivity.as_graphene_enum()(required=True)
        social_interaction_importance = SocialInteractionImportance.as_graphene_enum()(required=True)
        preferred_party_size = PreferredPartySize.as_graphene_enum()(required=True)
        physical_activity_satisfaction = PhysicalActivitySatisfaction.as_graphene_enum()(required=True)
        matched_participation_likelihood = MatchedParticipationLikelihood.as_graphene_enum()(required=True)
        formed_relationship_types = graphene.List(
            FormedRelationshipsType.as_graphene_enum()
        )
        preferred_partner_characteristics = graphene.List(
            PreferredPartnerCharacteristics.as_graphene_enum()
        )
        preferred_time_of_the_day = graphene.List(
            TimeOfTheDay.as_graphene_enum()
        )

    my_profile = graphene.Field(ProfileType)

    @classmethod
    def mutate(
        cls, 
        root, 
        info,
        frequency_of_physical_activity: FrequencyOfPhycicalActivity,
        social_interaction_importance: SocialInteractionImportance,
        preferred_party_size: PreferredPartySize,
        physical_activity_satisfaction: PhysicalActivitySatisfaction,
        matched_participation_likelihood: MatchedParticipationLikelihood,
        formed_relationship_types: list = [],
        preferred_partner_characteristics: list = [],
        preferred_time_of_the_day: list = [],
        **kwargs
        ):

        user: User = info.context.user
        if not user.id: raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)

        user.frequency_of_physical_activity = frequency_of_physical_activity
        user.social_interaction_importance = social_interaction_importance
        user.preferred_party_size = preferred_party_size
        user.physical_activity_satisfaction = physical_activity_satisfaction
        user.matched_participation_likelihood = matched_participation_likelihood
        user.formed_relationship_types = formed_relationship_types
        user.preferred_partner_characteristics = preferred_partner_characteristics
        user.preferred_time_of_the_day = preferred_time_of_the_day

        user.save()

        return SubmitSurveyMutation(my_profile = user)
        

class Mutation(graphene.ObjectType):
    submit_survey = SubmitSurveyMutation.Field()
    submit_basic_info = BasicInfoMutation.Field()
