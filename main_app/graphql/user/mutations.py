import graphene

from main_app.graphql.user.types import ProfileType
from main_app.validators import profile_validator

from ...models.enums import Gender
from ..error import MUError, MUErrorCode
from ...models import MoveusUser
from ...models.enums import (
    FrequencyOfPhycicalActivity,
    SocialInteractionImportance,
    PreferredPartySize,
    FormedRelationshipsType,
    PhysicalActivitySatisfaction,
    PreferredPartnerCharacteristics,
    MatchedParticipationLikelihood
)

class BasicInfoMutatuon(graphene.Mutation):

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
        
        user: MoveusUser = info.context.user
        if not user.id: raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)

        profile_validator(first_name, last_name, date_of_birth, bio)

        if first_name is not None: user.first_name = first_name
        if last_name is not None: user.last_name = last_name
        if date_of_birth: user.date_of_birth = date_of_birth
        if bio is not None : user.bio = bio
        if gender: user.gender = gender

        user.save()

        return BasicInfoMutatuon(my_profile = user)

class SubmitSurveyMutation(graphene.Mutation):

    class Arguments:
        nff = graphene.Boolean()
        fpa = FrequencyOfPhycicalActivity.as_graphene_enum()(required=True)
        sii = SocialInteractionImportance.as_graphene_enum()(required=True)
        pps = PreferredPartySize.as_graphene_enum()(required=True)
        pas = PhysicalActivitySatisfaction.as_graphene_enum()(required=True)
        mpl = MatchedParticipationLikelihood.as_graphene_enum()(required=True)
        frt = graphene.List(
            FormedRelationshipsType.as_graphene_enum()
        )
        ppc = graphene.List(
            PreferredPartnerCharacteristics.as_graphene_enum()
        )

    my_profile = graphene.Field(ProfileType)

    @classmethod
    def mutate(
        cls, 
        root, 
        info,
        nff: bool,
        fpa: FrequencyOfPhycicalActivity,
        sii: SocialInteractionImportance,
        pps: PreferredPartySize,
        pas: PhysicalActivitySatisfaction,
        mpl: MatchedParticipationLikelihood,
        frt: list = [],
        ppc: list = [],
        **kwargs
        ):

        user: MoveusUser = info.context.user
        if not user.id: raise MUError(MUErrorCode.AUTHENTIFICATION_ERROR)

        user.new_friendships_formed = nff
        user.frequency_of_physical_activity = fpa
        user.social_iteraction_importance = sii
        user.preferred_party_size = pps
        user.physical_activity_satisfaction = pas
        user.matched_participation_likelihood = mpl
        user.formed_relationships_type = frt
        user.preferred_partned_characteristics = ppc

        user.save()

        return SubmitSurveyMutation(my_profile = user)
        

class Mutation(graphene.ObjectType):
    submit_survey = SubmitSurveyMutation.Field()
    basic_info = BasicInfoMutatuon.Field()
