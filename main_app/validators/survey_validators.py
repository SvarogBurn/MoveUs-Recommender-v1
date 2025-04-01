from .validation_error import ValidationError
from models.enums import (
    FrequencyOfPhycicalActivity,
    SocialInteractionImportance,
    PreferredPartySize,
    FormedRelationshipsType,
    PhysicalActivitySatisfaction,
    PreferredPartnerCharacteristics,
    MatchedParticipationLikelihood
)

def survey_validator(**kwargs):
    
    fpa = kwargs['fpa']
    if not fpa or not type(fpa) == int or not 0 <= fpa < len(FrequencyOfPhycicalActivity):
         raise ValidationError("Missing or invalid frequency of physical activity value.")