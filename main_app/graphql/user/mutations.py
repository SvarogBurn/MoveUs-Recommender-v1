import graphene
from graphql import GraphQLError

from main_app.graphql.user.types import UserType

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

    profile = graphene.Field(UserType)

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

        if not user.id: raise GraphQLError("Not authentificated")

        user.new_friendships_formed = nff
        user.frequency_of_physical_activity = fpa
        user.social_iteraction_importance = sii
        user.preferred_party_size = pps
        user.physical_activity_satisfaction = pas
        user.matched_participation_likelihood = mpl
        user.formed_relationships_type = frt
        user.preferred_partned_characteristics = ppc

        user.save()

        return SubmitSurveyMutation(profile = user)
        

class Mutation(graphene.ObjectType):
    submit_survey = SubmitSurveyMutation.Field()
