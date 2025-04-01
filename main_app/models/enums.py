from enum import IntEnum

import graphene

class BaseEnum(IntEnum):

    @classmethod
    def choices(self):
        return [(key.value, key.name) for key in self]
    
    @classmethod
    def as_graphene_enum(self):
        return graphene.Enum.from_enum(self)
    
class PrivacyScope(BaseEnum):
    NOONE = 0
    FRIENDS = 1
    EVERYONE = 2

class FrequencyOfPhycicalActivity(BaseEnum):
    DAILY = 0
    FEW_TIMES_A_WEEK = 1
    ONCE_A_WEEK = 2
    OCCASIONALLY = 3
    RARELY = 4

class SkillLevel(BaseEnum):
    BEGINNER = 0
    INTERMEDIATE = 1
    ADVANCED = 2
    EXPERT = 3

class SocialInteractionImportance(BaseEnum):
    VERY_IMPORTANT = 0
    SOMEWHAT_IMPORTANT = 1
    NEUTRAL = 2
    NOT_VERY_IMPORTANT = 3
    NOT_IMPORTANT_AT_ALL = 4

class PreferredPartySize(BaseEnum):
    ALONE = 0
    SMALL_GROUP = 1
    LARGE_GROUP = 2

class FormedRelationshipsType(BaseEnum):
    ACQUAINTANCES = 0
    FRIENDS = 1
    ROMANTIC_RELATIONSHIPS = 2

class PhysicalActivitySatisfaction(BaseEnum):
    VERY_SATISFIED = 0
    SATISFIED = 1
    NEUTRAL = 2
    DISSATISFIED = 3
    VERY_DISSATISFIED = 4

class PreferredPartnerCharacteristics(BaseEnum):
    SIMILAR_SKILL_LEVEL = 0
    SIMILAR_AGE = 1
    SAME_GENDER = 2
    SIMILAR_INTERESTS = 3
    SIMILAR_HEALTH_GOALS = 4
    PROXIMITY = 5
    SIMILAR_HOBBIES = 6

class MatchedParticipationLikelihood(BaseEnum):
    VERY_LIKELY = 0
    LIKELY = 1
    NEUTRAL = 2
    UNLIKELY = 3
    VERY_UNLIKELY = 4

class MemberRole(BaseEnum):
    PARTICIPANT = 0
    ORGANIZER = 1
    MODERATOR = 2
    SPECTATOR = 3

class ChatNotifications(BaseEnum):
    NONE = 0
    ALL = 1
    MENTIONS_ONLY = 2

class EventRating(BaseEnum):
    VERY_BAD = 0
    BAD = 1
    NEUTRAL = 2
    GOOD = 3
    GREAT = 4

class RelationshipStatus(BaseEnum):
    NONE = 0
    PENDING = 1
    FRIENDS = 2
    BLOCKED_BY_FIRST = 3
    BLOCKED_BY_SECOND = 4
    BLOCKED_BY_BOTH = 5

class PersonalityTrait(BaseEnum):
    INTROVERSION = 0

class PrivacySetting(BaseEnum):
    LOCATION = 0
    AGE = 1
    FRIENDS = 2
    EMAIL = 3
    GENDER = 4

class OtherOption(BaseEnum):
    PREFERRED_PARTNER_CHARACTHERISTICS = 0
    ACTIVITY = 1
    FORMED_RELATIONSHIPS_TYPE = 2

class Gender(BaseEnum):
    MALE = 0
    FEMALE = 1
    NON_BINARY = 2
    PREFFER_NOT_TO_SAY = 3