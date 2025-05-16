from enum import Enum, IntEnum

import graphene


class BaseEnum():

    @classmethod
    def choices(self):
        return [(key.value, key.name) for key in self]
    
    @classmethod
    def as_graphene_enum(self):
        return graphene.Enum.from_enum(self)
    
class BaseIntEnum(BaseEnum, IntEnum):
    pass

class BaseStringEnum(BaseEnum, Enum):
    pass

class PrivacyScope(BaseIntEnum):
    NOONE = 0
    FRIENDS = 1
    EVERYONE = 2

class FrequencyOfPhycicalActivity(BaseIntEnum):
    DAILY = 0
    FEW_TIMES_A_WEEK = 1
    ONCE_A_WEEK = 2
    OCCASIONALLY = 3
    RARELY = 4

class SkillLevel(BaseIntEnum):
    BEGINNER = 0
    INTERMEDIATE = 1
    ADVANCED = 2
    EXPERT = 3

class SocialInteractionImportance(BaseIntEnum):
    VERY_IMPORTANT = 0
    SOMEWHAT_IMPORTANT = 1
    NEUTRAL = 2
    NOT_VERY_IMPORTANT = 3
    NOT_IMPORTANT_AT_ALL = 4

class PreferredPartySize(BaseIntEnum):
    ALONE = 0
    SMALL_GROUP = 1
    LARGE_GROUP = 2

class FormedRelationshipsType(BaseIntEnum):
    ACQUAINTANCES = 0
    FRIENDS = 1
    ROMANTIC_RELATIONSHIPS = 2

class PhysicalActivitySatisfaction(BaseIntEnum):
    VERY_SATISFIED = 0
    SATISFIED = 1
    NEUTRAL = 2
    DISSATISFIED = 3
    VERY_DISSATISFIED = 4

class PreferredPartnerCharacteristics(BaseIntEnum):
    SIMILAR_SKILL_LEVEL = 0
    SIMILAR_AGE = 1
    SAME_GENDER = 2
    SIMILAR_INTERESTS = 3
    SIMILAR_HEALTH_GOALS = 4
    PROXIMITY = 5
    SIMILAR_HOBBIES = 6

class MatchedParticipationLikelihood(BaseIntEnum):
    VERY_LIKELY = 0
    LIKELY = 1
    NEUTRAL = 2
    UNLIKELY = 3
    VERY_UNLIKELY = 4

class MemberRole(BaseIntEnum):
    SPECTATOR = 0
    PARTICIPANT = 1
    MODERATOR = 2
    ORGANIZER = 3

class ChatNotifications(BaseIntEnum):
    NONE = 0
    ALL = 1
    MENTIONS_ONLY = 2

class EventRating(BaseIntEnum):
    VERY_BAD = 0
    BAD = 1
    NEUTRAL = 2
    GOOD = 3
    GREAT = 4

class RelationshipStatus(BaseIntEnum):
    NONE = 0
    PENDING = 1
    FRIENDS = 2
    BLOCKED_BY_ONE = 3
    #BLOCKED_BY_SECOND = 4
    BLOCKED_BY_BOTH = 5
    REQUEST_SENT = 6
    REQUEST_RECEIVED = 7

class PersonalityTrait(BaseIntEnum):
    INTROVERSION = 0

class PrivacySetting(BaseIntEnum):
    LOCATION = 0
    AGE = 1
    FRIENDS = 2
    EMAIL = 3
    GENDER = 4

class OtherOption(BaseIntEnum):
    PREFERRED_PARTNER_CHARACTERISTICS = 0
    ACTIVITY = 1
    FORMED_RELATIONSHIPS_TYPE = 2
    
class Gender(BaseIntEnum):
    MALE = 0
    FEMALE = 1
    NON_BINARY = 2
    PREFER_NOT_TO_SAY = 3

class GenderNoPNTS(BaseIntEnum):
    MALE = 0
    FEMALE = 1
    NON_BINARY = 2

class TimeOfTheDay(BaseIntEnum):
    MORNING = 0
    AFTERNOON = 1
    EVENING = 2
    NIGHT = 3

class MainInterest(BaseIntEnum):
    SOCIALIZE = 0
    FUN = 1
    SPORT = 2

class ActivityEnum(BaseIntEnum):
    HIKING = 0
    RUNNING = 1
    SOCCER = 2
    TENNIS = 3
    GYM = 4

class NotificationEnum(BaseIntEnum):
    FRIEND_REQUEST = 0
    FRIEND_ACCEPTED = 1
    EVENT_FINISHED = 2

class CountryCode(BaseStringEnum):
    AF = 1   # Afghanistan
    AL = 2   # Albania
    DZ = 3   # Algeria
    AS = 4   # American Samoa
    AD = 5   # Andorra
    AO = 6   # Angola
    AI = 7   # Anguilla
    AQ = 8   # Antarctica
    AG = 9   # Antigua and Barbuda
    AR = 10  # Argentina
    AM = 11  # Armenia
    AW = 12  # Aruba
    AU = 13  # Australia
    AT = 14  # Austria
    AZ = 15  # Azerbaijan
    BS = 16  # Bahamas
    BH = 17  # Bahrain
    BD = 18  # Bangladesh
    BB = 19  # Barbados
    BY = 20  # Belarus
    BE = 21  # Belgium
    BZ = 22  # Belize
    BJ = 23  # Benin
    BM = 24  # Bermuda
    BT = 25  # Bhutan
    BO = 26  # Bolivia
    BA = 27  # Bosnia and Herzegovina
    BW = 28  # Botswana
    BR = 29  # Brazil
    IO = 30  # British Indian Ocean Territory
    BN = 31  # Brunei Darussalam
    BG = 32  # Bulgaria
    BF = 33  # Burkina Faso
    BI = 34  # Burundi
    KH = 35  # Cambodia
    CM = 36  # Cameroon
    CA = 37  # Canada
    CV = 38  # Cape Verde
    KY = 39  # Cayman Islands
    CF = 40  # Central African Republic
    TD = 41  # Chad
    CL = 42  # Chile
    CN = 43  # China
    CO = 44  # Colombia
    KM = 45  # Comoros
    CG = 46  # Congo
    CD = 47  # Congo, Democratic Republic
    CK = 48  # Cook Islands
    CR = 49  # Costa Rica
    CI = 50  # Côte d'Ivoire
    HR = 51  # Croatia
    CU = 52  # Cuba
    CY = 53  # Cyprus
    CZ = 54  # Czech Republic
    DK = 55  # Denmark
    DJ = 56  # Djibouti
    DM = 57  # Dominica
    DO = 58  # Dominican Republic
    EC = 59  # Ecuador
    EG = 60  # Egypt
    SV = 61  # El Salvador
    GQ = 62  # Equatorial Guinea
    ER = 63  # Eritrea
    EE = 64  # Estonia
    SZ = 65  # Eswatini
    ET = 66  # Ethiopia
    FJ = 67  # Fiji
    FI = 68  # Finland
    FR = 69  # France
    GA = 70  # Gabon
    GM = 71  # Gambia
    GE = 72  # Georgia
    DE = 73  # Germany
    GH = 74  # Ghana
    GR = 75  # Greece
    GD = 76  # Grenada
    GT = 77  # Guatemala
    GN = 78  # Guinea
    GW = 79  # Guinea-Bissau
    GY = 80  # Guyana
    HT = 81  # Haiti
    HN = 82  # Honduras
    HU = 83  # Hungary
    IS = 84  # Iceland
    IN = 85  # India
    ID = 86  # Indonesia
    IR = 87  # Iran
    IQ = 88  # Iraq
    IE = 89  # Ireland
    IL = 90  # Israel
    IT = 91  # Italy
    JM = 92  # Jamaica
    JP = 93  # Japan
    JO = 94  # Jordan
    KZ = 95  # Kazakhstan
    KE = 96  # Kenya
    KI = 97  # Kiribati
    KP = 98  # Korea, North
    KR = 99  # Korea, South
    KW = 100  # Kuwait
    KG = 101  # Kyrgyzstan
    LA = 102  # Lao People's Democratic Republic
    LV = 103  # Latvia
    LB = 104  # Lebanon
    LS = 105  # Lesotho
    LR = 106  # Liberia
    LY = 107  # Libya
    LI = 108  # Liechtenstein
    LT = 109  # Lithuania
    LU = 110  # Luxembourg
    MG = 111  # Madagascar
    MW = 112  # Malawi
    MY = 113  # Malaysia
    MV = 114  # Maldives
    ML = 115  # Mali
    MT = 116  # Malta
    MH = 117  # Marshall Islands
    MR = 118  # Mauritania
    MU = 119  # Mauritius
    MX = 120  # Mexico
    FM = 121  # Micronesia
    MD = 122  # Moldova
    MC = 123  # Monaco
    MN = 124  # Mongolia
    ME = 125  # Montenegro
    MA = 126  # Morocco
    MZ = 127  # Mozambique
    MM = 128  # Myanmar
    NA = 129  # Namibia
    NR = 130  # Nauru
    NP = 131  # Nepal
    NL = 132  # Netherlands
    NZ = 133  # New Zealand
    NI = 134  # Nicaragua
    NE = 135  # Niger
    NG = 136  # Nigeria
    MK = 137  # North Macedonia
    NO = 138  # Norway
    OM = 139  # Oman
    PK = 140  # Pakistan
    PW = 141  # Palau
    PS = 142  # Palestine
    PA = 143  # Panama
    PG = 144  # Papua New Guinea
    PY = 145  # Paraguay
    PE = 146  # Peru
    PH = 147  # Philippines
    PL = 148  # Poland
    PT = 149  # Portugal
    QA = 150  # Qatar
    RO = 151  # Romania
    RU = 152  # Russian Federation
    RW = 153  # Rwanda
    KN = 154  # Saint Kitts and Nevis
    LC = 155  # Saint Lucia
    VC = 156  # Saint Vincent and the Grenadines
    WS = 157  # Samoa
    SM = 158  # San Marino
    ST = 159  # Sao Tome and Principe
    SA = 160  # Saudi Arabia
    SN = 161  # Senegal
    RS = 162  # Serbia
    SC = 163  # Seychelles
    SL = 164  # Sierra Leone
    SG = 165  # Singapore
    SK = 166  # Slovakia
    SI = 167  # Slovenia
    SB = 168  # Solomon Islands
    SO = 169  # Somalia
    ZA = 170  # South Africa
    SS = 171  # South Sudan
    ES = 172  # Spain
    LK = 173  # Sri Lanka
    SD = 174  # Sudan
    SR = 175  # Suriname
    SE = 176  # Sweden
    CH = 177  # Switzerland
    SY = 178  # Syria
    TW = 179  # Taiwan
    TJ = 180  # Tajikistan
    TZ = 181  # Tanzania
    TH = 182  # Thailand
    TL = 183  # Timor-Leste
    TG = 184  # Togo
    TO = 185  # Tonga
    TT = 186  # Trinidad and Tobago
    TN = 187  # Tunisia
    TR = 188  # Turkey
    TM = 189  # Turkmenistan
    TV = 190  # Tuvalu
    UG = 191  # Uganda
    UA = 192  # Ukraine
    AE = 193  # United Arab Emirates
    GB = 194  # United Kingdom
    US = 195  # United States
    UY = 196  # Uruguay
    UZ = 197  # Uzbekistan
    VU = 198  # Vanuatu
    VE = 199  # Venezuela
    VN = 200  # Vietnam
    YE = 201  # Yemen
    ZM = 202  # Zambia
    ZW = 203  # Zimbabwe