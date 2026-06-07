"""Static configuration for the synthetic data generator."""
from datetime import datetime

SEED = 42

# Scale
N_USERS = 10_000
N_EVENTS = 3_333
N_COLD_USERS = 1_000

# Temporal window (24 months)
START_DATE = datetime(2023, 1, 1)
TIME_SPAN_DAYS = 730

# Motivation archetypes (behavioural only)
MOTIVATION_ARCHETYPES = {
    "competitive": 0.15,
    "casual_recreational": 0.40,
    "social": 0.30,
    "unmotivated": 0.15,
}

# Frequency tier -> (lambda_low, lambda_high) and target midpoint
FREQUENCY_TIERS = {
    "sparse": (2, 6),
    "occasional": (12, 22),
    "regular": (28, 45),
    "frequent": (70, 120),
}
FREQ_TIER_TARGET = {"sparse": 4, "occasional": 17, "regular": 36, "frequent": 95}

FREQ_TIER_DIST = {
    "competitive":         {"sparse": 0.05, "occasional": 0.20, "regular": 0.45, "frequent": 0.30},
    "casual_recreational": {"sparse": 0.30, "occasional": 0.45, "regular": 0.20, "frequent": 0.05},
    "social":              {"sparse": 0.10, "occasional": 0.25, "regular": 0.40, "frequent": 0.25},
    "unmotivated":         {"sparse": 0.60, "occasional": 0.35, "regular": 0.05, "frequent": 0.00},
}

# Behavioural probabilities per archetype
RATE_PROB = {"competitive": 0.82, "casual_recreational": 0.60, "social": 0.67, "unmotivated": 0.48}
LEAVE_PROB = {"competitive": 0.04, "casual_recreational": 0.12, "social": 0.04, "unmotivated": 0.35}
RATING_NOISE = {"competitive": 0.35, "casual_recreational": 0.80, "social": 0.50, "unmotivated": 1.20}
SOCIAL_WEIGHT = {"competitive": 0.30, "casual_recreational": 0.60, "social": 1.20, "unmotivated": 0.90}

# Gender enum: [MALE, FEMALE, NON_BINARY, PREFER_NOT_TO_SAY]
GENDER_WEIGHTS = [0.48, 0.48, 0.02, 0.02]

# Personality-activity fit coefficients.
# Verbatim from Table 17 of workrefferences/syntheticdata.txt:
#   Openness x Risk tolerance        = 0.42  [84]
#   Extraversion x Social interaction = 0.42  [96]
#   Hardiness x Risk tolerance       = 0.75  [103]
#   Neuroticism x Risk tolerance     = -0.47 [84]
# Conscientiousness x Consistency demand has NO empirical coefficient in Table 17
# ("strong theoretical link via definition of conscientiousness"); set to a
# representative value within the range of Table-17 conscientiousness correlations
# (0.20-0.41) and treated as theoretical, not empirical.
FIT_COEFFICIENTS = {
    "O_risk": 0.42,
    "E_social": 0.42,
    "H_risk": 0.75,
    "N_risk": -0.47,
    "C_consistency": 0.40,  # theoretical
}
# Base rating rescale: rating ~ FIT_BASE_SCALE * fit + FIT_BASE_OFFSET
FIT_BASE_SCALE = 2.0
FIT_BASE_OFFSET = 1.0

# Sport clusters: 0=team 1=endurance 2=precision 3=risk 4=combat 5=mind-body 6=strength 7=aquatic
ACTIVITY_CLUSTER = {
    0: 1, 1: 1, 2: 0, 3: 2, 4: 6, 5: 5, 6: 2, 7: 0, 8: 0, 9: 1,
    10: 4, 11: 3, 12: 0, 13: 6, 14: 5, 15: 0, 16: 2, 17: 0, 18: 7,
    19: 4, 20: 5, 21: 0, 22: 7, 23: 3, 24: 3, 25: 3, 26: 7, 27: 7,
    28: 0, 29: 1, 30: 5,
}

# Flexible vs fixed headcount per activity (fixed = team/court formats).
_FIXED = {2, 3, 6, 7, 8, 12, 15, 16, 17, 21, 28}  # soccer, tennis, badminton, baseball,
# basketball, cricket, football, golf, handball, rugby, volleyball
ACTIVITY_FLEXIBLE_SIZE = {a: (a not in _FIXED) for a in range(31)}

# Per-cluster matching attributes (hand-authored representative values; see spec
# "Out of scope" - names are real sport attributes, values are not dataset-derived).
CLUSTER_ATTRS = {
    0: {"risk": 0.50, "consistency": 0.50, "social": 1.00, "injury": 0.60},
    1: {"risk": 0.30, "consistency": 0.80, "social": 0.20, "injury": 0.40},
    2: {"risk": 0.20, "consistency": 0.60, "social": 0.40, "injury": 0.30},
    3: {"risk": 1.00, "consistency": 0.30, "social": 0.30, "injury": 1.00},
    4: {"risk": 0.80, "consistency": 0.60, "social": 0.50, "injury": 0.80},
    5: {"risk": 0.10, "consistency": 0.70, "social": 0.80, "injury": 0.10},
    6: {"risk": 0.40, "consistency": 1.00, "social": 0.30, "injury": 0.50},
    7: {"risk": 0.70, "consistency": 0.40, "social": 0.50, "injury": 0.50},
}

# Activity sampling weights (power-law)
RAW_ACT_WEIGHTS = {
    0: 4, 1: 12, 2: 10, 3: 6, 4: 9, 5: 3, 6: 3, 7: 2, 8: 6, 9: 5, 10: 3,
    11: 3, 12: 1, 13: 4, 14: 3, 15: 4, 16: 2, 17: 2, 18: 1, 19: 2, 20: 2,
    21: 1, 22: 1, 23: 1, 24: 2, 25: 2, 26: 1, 27: 4, 28: 2, 29: 5, 30: 4,
}

# Geo clusters around Zagreb: (lat, lon, sigma)
GEO_CLUSTERS = [
    (45.813, 15.978, 0.010), (45.853, 15.952, 0.008), (45.795, 16.045, 0.009),
    (45.751, 15.975, 0.008), (45.812, 15.888, 0.009),
]

# Logit weights for the join probability
W_ACT, W_SKILL, W_DIST, W_AVAIL = 2.0, 1.5, 1.0, 0.8
W_ORG = 0.4              # organiser reputation (small)
W_SIZE, W_TIER, W_DUR, W_COMP = 0.8, 0.9, 0.6, 0.7

# Organiser eligibility: ~1 in 12 of users are host-eligible
ORGANIZER_FRACTION = 1.0 / 12.0

# Participation tiers (ParticipationGroupKind, ROMANTIC dropped)
PARTICIPATION_TIERS = [0, 1, 2]  # FIRST_HAND, SECOND_HAND, COMMON_INTERESTS
