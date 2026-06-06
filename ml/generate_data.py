#!/usr/bin/env python3
"""
Synthetic data generator for the MoveUs recommender system — v2.

Scale  : 10,000 users / 3,333 events / 1,000 cold-start users
Time   : 24 months (Jan 2023 – Dec 2024)
Target : ~300k interactions (join_rated, join_no_rate, leave)

User motivation archetypes (what drives attendance):
  competitive         15%  — performance/improvement; low N, high C+H; always rates
  casual_recreational 40%  — fun/variety/relaxation; high O; moderate everything
  social              30%  — community/friendship; high E+A; stays out of obligation
  unmotivated         15%  — low intrinsic drive; high N, low C; high leave rate

Each archetype is crossed with a frequency tier (sparse/occasional/regular/frequent)
drawn from archetype-specific distributions, so a casual user can be a frequent one.

Produces (ml/data/):
  users.csv              — 10,000 users with motivation_type + frequency_tier + participation_groups
  events.csv             — 3,333 events with skill_diversity + social_density
  interactions.csv       — all interaction rows (signal_type column)
  train.csv              — warm users: all BUT last interaction per user
  test.csv               — warm users: last interaction per user (LOO positive)
  train_implicit.csv     — warm users: positive implicit rows only (for BPR)
  cold_start_users.csv   — all interactions for held-out cold users

Run:  python ml/generate_data.py
"""

import warnings
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Reproducibility ───────────────────────────────────────────────────────────
SEED = 42

# ── Scale ─────────────────────────────────────────────────────────────────────
N_USERS      = 10_000
N_EVENTS     = 3_333
N_COLD_USERS = 1_000

# 24-month temporal window
START_DATE     = datetime(2023, 1, 1)
TIME_SPAN_DAYS = 730

# ── User archetype specification (motivation × frequency) ─────────────────────
# Motivation archetypes — what drives this person to attend sport events?
# Parameter values were elicited by describing each archetype to an LLM and
# asking for psychologically plausible Big Five and behaviour distributions,
# then cross-checked against sport-psychology literature.
MOTIVATION_ARCHETYPES: dict[str, float] = {
    "competitive":         0.15,   # performance/improvement-driven
    "casual_recreational": 0.40,   # fun, variety, relaxation
    "social":              0.30,   # community, friendship, belonging
    "unmotivated":         0.15,   # low intrinsic drive; needs external pull
}

# Frequency tier → (lambda_low, lambda_high) for Poisson interaction count
FREQUENCY_TIERS: dict[str, tuple[int, int]] = {
    "sparse":     (2,   6),
    "occasional": (12,  22),
    "regular":    (28,  45),
    "frequent":   (70, 120),
}

# P(frequency_tier | motivation_type) — motivation ≠ frequency; same archetype can go rarely
FREQ_TIER_DIST: dict[str, dict[str, float]] = {
    "competitive":         {"sparse": 0.05, "occasional": 0.20, "regular": 0.45, "frequent": 0.30},
    "casual_recreational": {"sparse": 0.30, "occasional": 0.45, "regular": 0.20, "frequent": 0.05},
    "social":              {"sparse": 0.10, "occasional": 0.25, "regular": 0.40, "frequent": 0.25},
    "unmotivated":         {"sparse": 0.60, "occasional": 0.35, "regular": 0.05, "frequent": 0.00},
}

# Big Five Beta(α, β) per motivation archetype (LLM-elicited, psychologically grounded)
ARCHETYPE_PERSONALITY: dict[str, dict[str, tuple[float, float]]] = {
    "competitive": {
        "O": (4.0, 2.5), "C": (6.0, 2.0), "E": (4.0, 4.0),
        "A": (3.5, 4.5), "N": (2.0, 6.0), "H": (6.0, 2.5),
    },
    "casual_recreational": {
        "O": (6.5, 2.0), "C": (3.5, 3.5), "E": (4.5, 4.0),
        "A": (5.0, 3.0), "N": (3.0, 5.0), "H": (4.0, 3.0),
    },
    "social": {
        "O": (4.5, 3.5), "C": (3.0, 5.0), "E": (7.0, 1.5),
        "A": (6.5, 2.0), "N": (3.5, 4.5), "H": (4.0, 3.5),
    },
    "unmotivated": {
        "O": (3.0, 4.5), "C": (2.0, 6.0), "E": (2.5, 5.5),
        "A": (5.0, 3.0), "N": (6.5, 2.5), "H": (2.0, 6.0),
    },
}

# P(explicit rating | join) — competitive users always rate; unmotivated rarely bother
RATE_PROB: dict[str, float] = {
    "competitive":         0.82,
    "casual_recreational": 0.60,
    "social":              0.67,
    "unmotivated":         0.48,
}

# P(leave before end | join) — unmotivated quit; social users stay out of obligation
LEAVE_PROB: dict[str, float] = {
    "competitive":         0.04,
    "casual_recreational": 0.12,
    "social":              0.04,
    "unmotivated":         0.35,
}

# Rating noise σ — competitive users are calibrated; unmotivated are erratic
RATING_NOISE: dict[str, float] = {
    "competitive":         0.35,
    "casual_recreational": 0.80,
    "social":              0.50,
    "unmotivated":         1.20,
}

# Social signal weight per motivation type — how much "organiser I follow" matters
SOCIAL_WEIGHT: dict[str, float] = {
    "competitive":         0.30,   # don't care about organiser identity
    "casual_recreational": 0.60,   # moderate social pull
    "social":              1.20,   # biggest driver: who organised, who's coming
    "unmotivated":         0.90,   # needs a friend as external motivation
}

# Activity → sport cluster (0-indexed; 8 clusters from HDBSCAN in thesis)
# 0=team  1=endurance  2=precision  3=risk/extreme
# 4=combat  5=mind-body  6=strength  7=aquatic
ACTIVITY_CLUSTER: dict[int, int] = {
    0: 1,   # HIKING
    1: 1,   # RUNNING
    2: 0,   # SOCCER
    3: 2,   # TENNIS
    4: 6,   # GYM
    5: 5,   # AEROBICS
    6: 2,   # BADMINTON
    7: 0,   # BASEBALL
    8: 0,   # BASKETBALL
    9: 1,   # BIKING
    10: 4,  # BOXING
    11: 3,  # CLIMBING
    12: 0,  # CRICKET
    13: 6,  # CROSSFIT
    14: 5,  # DANCING
    15: 0,  # FOOTBALL
    16: 2,  # GOLF
    17: 0,  # HANDBALL
    18: 7,  # KAYAKING
    19: 4,  # MARTIAL_ARTS
    20: 5,  # PILATES
    21: 0,  # RUGBY
    22: 7,  # SAILING
    23: 3,  # SKATEBOARDING
    24: 3,  # SKIING
    25: 3,  # SNOWBOARDING
    26: 7,  # SURFING
    27: 7,  # SWIMMING
    28: 0,  # VOLLEYBALL
    29: 1,  # WALKING
    30: 5,  # YOGA
}

# EFA factor scores per sport cluster (8 factors × 8 clusters)
CLUSTER_EFA: dict[int, list[float]] = {
    0: [0.90, 0.30, 0.50, 0.50, 0.20, 0.90, 0.40, 0.30],
    1: [0.80, 0.30, 0.30, 0.40, 0.60, 0.20, 0.50, 0.30],
    2: [0.40, 0.90, 0.20, 0.70, 0.30, 0.30, 0.30, 0.50],
    3: [0.50, 0.50, 0.90, 0.60, 0.80, 0.20, 0.50, 0.80],
    4: [0.80, 0.60, 0.70, 0.90, 0.20, 0.40, 0.80, 0.40],
    5: [0.30, 0.50, 0.10, 0.60, 0.30, 0.60, 0.40, 0.30],
    6: [0.70, 0.30, 0.30, 0.70, 0.20, 0.20, 0.90, 0.50],
    7: [0.50, 0.40, 0.60, 0.50, 0.90, 0.30, 0.40, 0.70],
}

# Per-cluster personality-matching attributes (Table 17)
CLUSTER_ATTRS: dict[int, dict[str, float]] = {
    0: {"risk": 0.50, "consistency": 0.50, "social": 1.00, "injury": 0.60},
    1: {"risk": 0.30, "consistency": 0.80, "social": 0.20, "injury": 0.40},
    2: {"risk": 0.20, "consistency": 0.60, "social": 0.40, "injury": 0.30},
    3: {"risk": 1.00, "consistency": 0.30, "social": 0.30, "injury": 1.00},
    4: {"risk": 0.80, "consistency": 0.60, "social": 0.50, "injury": 0.80},
    5: {"risk": 0.10, "consistency": 0.70, "social": 0.80, "injury": 0.10},
    6: {"risk": 0.40, "consistency": 1.00, "social": 0.30, "injury": 0.50},
    7: {"risk": 0.70, "consistency": 0.40, "social": 0.50, "injury": 0.50},
}

# Activity sampling weights (power-law: running, soccer, gym most frequent)
_RAW_ACT_WEIGHTS = {
    0: 4, 1: 12, 2: 10, 3: 6, 4: 9, 5: 3, 6: 3,
    7: 2, 8: 6, 9: 5, 10: 3, 11: 3, 12: 1, 13: 4,
    14: 3, 15: 4, 16: 2, 17: 2, 18: 1, 19: 2, 20: 2,
    21: 1, 22: 1, 23: 1, 24: 2, 25: 2, 26: 1, 27: 4,
    28: 2, 29: 5, 30: 4,
}
_ACT_IDS   = np.array(list(_RAW_ACT_WEIGHTS.keys()))
_ACT_PROBS = np.array(list(_RAW_ACT_WEIGHTS.values()), dtype=float)
_ACT_PROBS /= _ACT_PROBS.sum()

# 5 geographic clusters around Zagreb
GEO_CLUSTERS = [
    (45.813, 15.978, 0.010),
    (45.853, 15.952, 0.008),
    (45.795, 16.045, 0.009),
    (45.751, 15.975, 0.008),
    (45.812, 15.888, 0.009),
]

# Join-probability logit weights
W_ACT = 2.0; W_SKILL = 1.5; W_DIST = 1.0; W_AVAIL = 0.8; W_PERS = 1.2
W_SOCIAL = 0.6   # boost when organizer is followed
LOGIT_BIAS = -3.5


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def _haversine_km(lat1: float, lon1: float,
                  lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    R = 6_371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2))
         * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _personality_fit(O: float, C: float, E: float, N: float, H: float,
                     clusters: np.ndarray) -> np.ndarray:
    risk = np.array([CLUSTER_ATTRS[c]["risk"]        for c in clusters])
    cons = np.array([CLUSTER_ATTRS[c]["consistency"]  for c in clusters])
    soc  = np.array([CLUSTER_ATTRS[c]["social"]       for c in clusters])
    inj  = np.array([CLUSTER_ATTRS[c]["injury"]       for c in clusters])
    return (0.42 * O * risk + 0.45 * C * cons
            + 0.42 * E * soc - 0.47 * N * inj + 0.38 * H * risk)


def _participation_groups(E: float, group_size: int, rng: np.random.Generator) -> str:
    """Multi-hot ParticipationGroupKind (0=SOLO,1=PAIR,2=SMALL_GROUP,3=LARGE_GROUP)."""
    prefs = set()
    if E < 0.35 or group_size <= 2:
        prefs.add(0)
    if group_size <= 4 or E < 0.55:
        prefs.add(1)
    if group_size <= 9 or E > 0.30:
        prefs.add(2)
    if E > 0.60 or group_size >= 7:
        prefs.add(3)
    if not prefs:
        prefs = {2}
    # Small chance to add one random extra preference
    if rng.random() < 0.15:
        prefs.add(int(rng.integers(0, 4)))
    return ",".join(map(str, sorted(prefs)))


# ── Step 1: Generate users ────────────────────────────────────────────────────

def generate_users(rng: np.random.Generator) -> pd.DataFrame:
    n = N_USERS

    # Step A: Assign motivation archetype first — drives personality distributions
    _motiv_names = list(MOTIVATION_ARCHETYPES.keys())
    _motiv_fracs = np.array([MOTIVATION_ARCHETYPES[t] for t in _motiv_names])
    _motiv_ids   = rng.choice(len(_motiv_names), size=n, p=_motiv_fracs)
    motivation_type_col = [_motiv_names[i] for i in _motiv_ids]

    # Step B: Frequency tier — independent of personality; same motivation can go rarely
    _tier_names = ["sparse", "occasional", "regular", "frequent"]
    frequency_tier_col = [
        str(rng.choice(_tier_names, p=np.array([FREQ_TIER_DIST[mt][t] for t in _tier_names])))
        for mt in motivation_type_col
    ]

    # Step C: Big Five per archetype (LLM-elicited Beta parameters)
    O  = np.zeros(n); C  = np.zeros(n); E  = np.zeros(n)
    A  = np.zeros(n); N_ = np.zeros(n); H  = np.zeros(n)
    for mt in _motiv_names:
        mask = np.array([m == mt for m in motivation_type_col])
        if not mask.any():
            continue
        ab   = ARCHETYPE_PERSONALITY[mt]
        n_mt = int(mask.sum())
        O[mask]  = rng.beta(ab["O"][0], ab["O"][1], n_mt)
        C[mask]  = rng.beta(ab["C"][0], ab["C"][1], n_mt)
        E[mask]  = rng.beta(ab["E"][0], ab["E"][1], n_mt)
        A[mask]  = rng.beta(ab["A"][0], ab["A"][1], n_mt)
        N_[mask] = rng.beta(ab["N"][0], ab["N"][1], n_mt)
        H[mask]  = rng.beta(ab["H"][0], ab["H"][1], n_mt)
    Cf = rng.beta(4, 3, n)
    Lc = rng.beta(4, 3, n)

    # EFA factors
    fa = np.clip(0.5*C + 0.3*H + 0.2*(1-N_) + rng.normal(0, 0.05, n), 0, 1)
    fb = np.clip(0.4*E + 0.3*(1-N_) + 0.3*A  + rng.normal(0, 0.05, n), 0, 1)

    # UserPreferences fields
    pref_dur   = np.clip(90 - 30*C + 20*E + rng.normal(0, 15, n), 30, 180).astype(int)
    org_open   = np.where(E < 0.35, 0, np.where(E < 0.65, 1, 2))
    leadership = np.clip(np.round(1 + 4*E  + rng.normal(0, 0.5, n)), 1, 5).astype(int)
    max_travel = np.clip(5 + 45*(1-N_)*(0.5+0.5*H) + rng.normal(0, 5, n), 2, 50).astype(int)
    weekly_tgt = np.clip(np.round(1 + 6*C  + rng.normal(0, 0.5, n)), 1, 7).astype(int)
    pushes     = np.clip(np.round(1 + 4*(0.6*C+0.4*H) + rng.normal(0, 0.4, n)), 1, 5).astype(int)
    group_size = np.clip(np.round(2 + 8*E  + rng.normal(0, 1, n)), 1, 10).astype(int)
    acquaint   = np.clip(np.round(4*(1-N_) + rng.normal(0, 0.5, n)), 0, 4).astype(int)
    enjoy_new  = np.clip(np.round(1 + 4*E  + rng.normal(0, 0.5, n)), 1, 5).astype(int)
    act_soc    = np.clip(np.round(1 + 4*E  + rng.normal(0, 1, n)), 1, 5).astype(int)
    mot_comp   = np.clip(np.round(1 + 4*(0.5*Cf+0.5*Lc) + rng.normal(0, 0.5, n)), 1, 5).astype(int)
    planning   = np.clip(np.round(1 + 4*C  + rng.normal(0, 0.4, n)), 1, 5).astype(int)
    burden     = np.clip(np.round(1 + 4*N_ + rng.normal(0, 0.4, n)), 1, 5).astype(int)

    ages    = rng.integers(16, 65, n)
    genders = rng.integers(0, 4, n)

    geo_cls = rng.integers(0, len(GEO_CLUSTERS), n)
    lats = np.array([rng.normal(GEO_CLUSTERS[c][0], GEO_CLUSTERS[c][2]) for c in geo_cls])
    lngs = np.array([rng.normal(GEO_CLUSTERS[c][1], GEO_CLUSTERS[c][2]) for c in geo_cls])

    # Preferred activities (1–4, personality-weighted)
    pref_acts_col: list[str] = []
    pref_skills_col: list[str] = []
    for i in range(n):
        n_prefs = int(rng.integers(1, 5))
        w = np.array([
            max(0.42*O[i]*CLUSTER_ATTRS[ACTIVITY_CLUSTER[a]]["risk"]
                + 0.45*C[i]*CLUSTER_ATTRS[ACTIVITY_CLUSTER[a]]["consistency"]
                + 0.42*E[i]*CLUSTER_ATTRS[ACTIVITY_CLUSTER[a]]["social"]
                - 0.47*N_[i]*CLUSTER_ATTRS[ACTIVITY_CLUSTER[a]]["injury"]
                + 0.38*H[i]*CLUSTER_ATTRS[ACTIVITY_CLUSTER[a]]["risk"] + 1.0, 0.01)
            for a in range(31)
        ])
        w /= w.sum()
        chosen = rng.choice(31, size=n_prefs, replace=False, p=w)
        skills = rng.integers(0, 4, n_prefs)
        pref_acts_col.append(",".join(map(str, chosen.tolist())))
        pref_skills_col.append(",".join(map(str, skills.tolist())))

    avail_days_col:  list[str] = []
    avail_times_col: list[str] = []
    for i in range(n):
        n_slots = int(rng.integers(3, 10))
        days  = rng.choice(7, size=min(n_slots, 7), replace=False)
        times = rng.choice(4, size=min(n_slots, 4), replace=False)
        avail_days_col.append(",".join(map(str, sorted(days.tolist()))))
        avail_times_col.append(",".join(map(str, sorted(times.tolist()))))

    # Participation groups (multi-hot ParticipationGroupKind)
    part_groups_col = [
        _participation_groups(float(E[i]), int(group_size[i]), rng)
        for i in range(n)
    ]

    user_cluster = np.where((fa > 0.6) & (fb > 0.5), 0, np.where(fa > 0.5, 1, 2))

    return pd.DataFrame({
        "user_id":                    np.arange(n),
        "motivation_type":            motivation_type_col,
        "frequency_tier":             frequency_tier_col,
        "openness":                   O.round(4),
        "conscientiousness":          C.round(4),
        "extraversion":               E.round(4),
        "agreeableness":              A.round(4),
        "neuroticism":                N_.round(4),
        "hardiness":                  H.round(4),
        "confidence":                 Cf.round(4),
        "locus_of_control":           Lc.round(4),
        "fa_score":                   fa.round(4),
        "fb_score":                   fb.round(4),
        "preferred_session_duration": pref_dur,
        "organizing_openness":        org_open,
        "leadership_inclination":     leadership,
        "max_travel_distance":        max_travel,
        "weekly_activity_target":     weekly_tgt,
        "pushes_through_discomfort":  pushes,
        "preferred_group_size":       group_size,
        "acquaintance_preference":    acquaint,
        "enjoys_meeting_new_people":  enjoy_new,
        "activity_vs_social":         act_soc,
        "motivated_by_competition":   mot_comp,
        "planning_horizon":           planning,
        "feels_like_burden":          burden,
        "age":                        ages,
        "gender":                     genders,
        "latitude":                   lats.round(6),
        "longitude":                  lngs.round(6),
        "geo_cluster":                geo_cls,
        "user_cluster":               user_cluster,
        "preferred_activities":       pref_acts_col,
        "preferred_skills":           pref_skills_col,
        "availability_days":          avail_days_col,
        "availability_times":         avail_times_col,
        "participation_groups":       part_groups_col,
    })


# ── Step 2: Generate events ───────────────────────────────────────────────────

def generate_events(rng: np.random.Generator) -> pd.DataFrame:
    n = N_EVENTS

    activities    = rng.choice(_ACT_IDS, size=n, p=_ACT_PROBS)
    sport_cluster = np.array([ACTIVITY_CLUSTER[int(a)] for a in activities])
    skill_levels  = np.clip(np.floor(rng.beta(1.5, 3, n) * 4), 0, 3).astype(int)
    max_parts     = np.clip(np.round(np.exp(rng.normal(np.log(8), 0.6, n))), 2, 50).astype(int)
    dur_hours     = np.clip(rng.normal(1.5, 0.5, n), 0.5, 4.0).round(1)

    # Temporal pattern over 24 months
    day_offsets = rng.integers(0, TIME_SPAN_DAYS, n)
    is_evening  = rng.random(n) < 0.6
    hours       = np.where(is_evening, rng.integers(18, 21, n), rng.integers(9, 12, n))
    time_cats   = np.where(is_evening, 2, 0)
    weekdays    = (day_offsets % 7).astype(int)
    timestamps  = [
        START_DATE + timedelta(days=int(d), hours=int(h))
        for d, h in zip(day_offsets, hours)
    ]

    geo_cls = rng.integers(0, len(GEO_CLUSTERS), n)
    lats = np.array([rng.normal(GEO_CLUSTERS[c][0], GEO_CLUSTERS[c][2]) for c in geo_cls])
    lngs = np.array([rng.normal(GEO_CLUSTERS[c][1], GEO_CLUSTERS[c][2]) for c in geo_cls])

    efa_arrays: dict[str, list[float]] = {f"f{j+1}": [] for j in range(8)}
    for c in sport_cluster:
        base = CLUSTER_EFA[int(c)]
        for j in range(8):
            efa_arrays[f"f{j+1}"].append(float(np.clip(base[j] + rng.normal(0, 0.05), 0, 1)))

    fill_rate         = rng.beta(2, 3, n).round(3)
    participant_count = np.round(fill_rate * max_parts).astype(int)

    # Skill diversity: std of participant skill levels (synthetic approximation)
    # Power-law: uniform for beginner-friendly events, wide spread for mixed events
    skill_diversity = np.clip(
        rng.beta(1.5, 1.5, n) * 1.5, 0.0, 1.5
    ).round(3)

    # Social density category: 0=solo/pair(<3), 1=small(3-8), 2=large(>8)
    social_density_cat = np.where(
        participant_count < 3, 0, np.where(participant_count <= 8, 1, 2)
    ).astype(int)

    # Synthetic average organizer rating (Beta skewed positive)
    avg_organizer_rating = np.clip(rng.beta(4, 2, n) * 4.0, 0.0, 4.0).round(2)

    # Assign one warm user per event as organiser (used for social features)
    n_warm = N_USERS - N_COLD_USERS
    organizer_ids = rng.integers(0, n_warm, n)

    df = pd.DataFrame({
        "event_id":             np.arange(n),
        "organizer_id":         organizer_ids,
        "activity_id":          activities,
        "sport_cluster":        sport_cluster,
        "skill_level":          skill_levels,
        "max_participants":     max_parts,
        "duration_hours":       dur_hours,
        "start_time":           timestamps,
        "latitude":             lats.round(6),
        "longitude":            lngs.round(6),
        "geo_cluster":          geo_cls,
        "day_of_week":          weekdays,
        "time_of_day":          time_cats,
        "fill_rate":            fill_rate,
        "participant_count":    participant_count,
        "skill_diversity":      skill_diversity,
        "social_density_cat":   social_density_cat,
        "avg_organizer_rating": avg_organizer_rating,
    })
    for col, vals in efa_arrays.items():
        df[col] = np.round(vals, 4)
    return df


# ── Step 3: Follow network ────────────────────────────────────────────────────

def generate_follows(users_df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """
    Realistic follow network: extraversion drives follow count; same geo cluster → 4×
    weight. Average ~extraversion × 10 follows per user. Only warm users follow.
    """
    n = len(users_df)
    extraversion = users_df["extraversion"].values
    geo_cls      = users_df["geo_cluster"].values
    geo_to_users = {gc: np.where(geo_cls == gc)[0] for gc in np.unique(geo_cls)}
    n_warm        = N_USERS - N_COLD_USERS

    rows: list[dict] = []
    for uid in range(n_warm):
        n_follows = int(rng.poisson(max(1, extraversion[uid] * 10)))
        if n_follows == 0:
            continue
        gc = int(geo_cls[uid])
        same_gc = geo_to_users[gc]
        same_gc = same_gc[same_gc != uid]

        chosen: set = set()
        # 80 % from same geo cluster
        n_local = min(int(n_follows * 0.8), len(same_gc))
        if n_local > 0:
            chosen.update(rng.choice(same_gc, n_local, replace=False).tolist())
        # 20 % global
        n_global = max(0, n_follows - n_local)
        if n_global > 0:
            pool = np.arange(n_warm)
            pool = pool[pool != uid]
            chosen.update(rng.choice(pool, min(n_global, len(pool)), replace=False).tolist())
        chosen.discard(uid)

        for fid in chosen:
            rows.append({"follower_id": uid, "following_id": int(fid)})

    df = (pd.DataFrame(rows, columns=["follower_id", "following_id"])
          if rows else pd.DataFrame(columns=["follower_id", "following_id"]))
    return df.drop_duplicates().reset_index(drop=True)


# ── Step 4: Join probabilities (vectorised per user) ─────────────────────────

def _join_probs(user: pd.Series, events_df: pd.DataFrame,
                follows_set: frozenset | None = None,
                w_social: float = W_SOCIAL) -> np.ndarray:
    act_ids  = events_df["activity_id"].values
    clusters = events_df["sport_cluster"].values

    user_preferred  = set(map(int, str(user["preferred_activities"]).split(",")))
    user_pref_clust = {ACTIVITY_CLUSTER[a] for a in user_preferred}

    act_match = np.where(
        np.isin(act_ids, list(user_preferred)), 1.0,
        np.where(np.isin(clusters, list(user_pref_clust)), 0.6, 0.1),
    )

    user_pref_skills = dict(zip(
        map(int, str(user["preferred_activities"]).split(",")),
        map(int, str(user["preferred_skills"]).split(",")),
    ))
    default_skill = max(0, min(3, int(user["pushes_through_discomfort"]) // 2))
    u_skills = np.array([user_pref_skills.get(int(act_ids[i]), default_skill)
                         for i in range(len(events_df))])
    skill_compat = np.exp(-0.5 * ((events_df["skill_level"].values - u_skills) / 0.8) ** 2)

    dists = _haversine_km(float(user["latitude"]), float(user["longitude"]),
                          events_df["latitude"].values, events_df["longitude"].values)
    max_km     = max(float(user["max_travel_distance"]), 1.0)
    dist_score = np.exp(-dists / max_km)

    user_days  = set(map(int, str(user["availability_days"]).split(",")))
    user_times = set(map(int, str(user["availability_times"]).split(",")))
    avail_score = (
        np.isin(events_df["day_of_week"].values,  list(user_days)).astype(float)
        * np.isin(events_df["time_of_day"].values, list(user_times)).astype(float)
    )

    pers_fit = _personality_fit(
        float(user["openness"]), float(user["conscientiousness"]),
        float(user["extraversion"]), float(user["neuroticism"]),
        float(user["hardiness"]), clusters,
    )

    # Social signal: boost if user follows event organiser
    social_score = np.zeros(len(events_df), float)
    if follows_set and "organizer_id" in events_df.columns:
        org_ids = events_df["organizer_id"].values
        social_score = np.where(np.isin(org_ids, list(follows_set)), 1.0, 0.0)

    logit = (W_ACT*act_match + W_SKILL*skill_compat + W_DIST*dist_score
             + W_AVAIL*avail_score + W_PERS*pers_fit
             + w_social*social_score + LOGIT_BIAS)
    return _sigmoid(logit)


# ── Step 5: Rating generation ─────────────────────────────────────────────────

def _rating(user: pd.Series, event: pd.Series,
            motivation_type: str, rng: np.random.Generator) -> int:
    c  = int(event["sport_cluster"])
    ca = CLUSTER_ATTRS[c]
    fit = (0.42 * float(user["openness"])          * ca["risk"]
           + 0.45 * float(user["conscientiousness"]) * ca["consistency"]
           + 0.42 * float(user["extraversion"])      * ca["social"]
           - 0.47 * float(user["neuroticism"])       * ca["injury"]
           + 0.38 * float(user["hardiness"])         * ca["risk"])
    base = fit * 3.0 + 1.0

    if motivation_type == "unmotivated":
        # Bimodal: either genuinely inspired or disengaged
        if rng.random() < 0.55:
            raw = base + rng.normal(0, RATING_NOISE[motivation_type])
        else:
            raw = float(rng.choice([0.0, 4.0]))
    elif motivation_type == "competitive":
        # Penalise events where skill mismatch is large (too easy feels boring)
        skill_gap = abs(int(event["skill_level"]) - max(0, int(user["pushes_through_discomfort"]) // 2))
        raw = base - 0.5 * skill_gap + rng.normal(0, RATING_NOISE[motivation_type])
    elif motivation_type == "social":
        # Upward-biased regardless of activity fit — the people make the experience
        raw = base * 0.6 + 2.4 + rng.normal(0, RATING_NOISE[motivation_type])
    else:
        raw = base + rng.normal(0, RATING_NOISE[motivation_type])

    return int(np.clip(round(raw), 0, 4))


# ── Step 6: Generate all interactions ────────────────────────────────────────

def generate_interactions(
    users_df: pd.DataFrame,
    events_df: pd.DataFrame,
    rng: np.random.Generator,
    follows_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    # Build per-user follow set lookup {uid → frozenset(following_ids)}
    user_follows: dict[int, frozenset] = {}
    if follows_df is not None and len(follows_df) > 0:
        for uid, grp in follows_df.groupby("follower_id"):
            user_follows[int(uid)] = frozenset(grp["following_id"].astype(int).tolist())

    rows: list[dict] = []

    type_time_bias: dict[str, float] = {
        "competitive":         0.55,
        "casual_recreational": 0.50,
        "social":              0.55,
        "unmotivated":         0.30,
    }

    for _, user in users_df.iterrows():
        motivation_type = str(user["motivation_type"])
        frequency_tier  = str(user["frequency_tier"])
        lam_lo, lam_hi  = FREQUENCY_TIERS[frequency_tier]
        lam = float(rng.uniform(lam_lo, lam_hi))
        n_ints = int(np.clip(rng.poisson(lam), 1, N_EVENTS))

        uid = int(user["user_id"])
        follows_set = user_follows.get(uid)
        w_social = SOCIAL_WEIGHT[motivation_type]
        probs = _join_probs(user, events_df, follows_set=follows_set, w_social=w_social)
        s = probs.sum()
        probs = probs / s if s > 0 else np.ones(N_EVENTS) / N_EVENTS

        chosen_idxs = rng.choice(len(events_df), size=n_ints, replace=False, p=probs)

        for idx in chosen_idxs:
            event = events_df.iloc[int(idx)]

            # Determine signal type
            r_roll = rng.random()
            l_roll = rng.random()
            if l_roll < LEAVE_PROB[motivation_type]:
                signal_type = "leave"
                rating      = None
                label       = 0
            elif r_roll < RATE_PROB[motivation_type]:
                signal_type = "join_rated"
                rating      = _rating(user, event, motivation_type, rng)
                label       = 1 if rating >= 3 else 0
            else:
                signal_type = "join_no_rate"
                rating      = None
                label       = 1   # implicit positive

            # implicit_label: +1 for any positive join, -1 for leave
            implicit_label = -1 if signal_type == "leave" else 1

            # Signal weight for weighted training
            if signal_type == "join_rated":
                weight = 3.0 if label == 1 else 2.0
            elif signal_type == "join_no_rate":
                weight = 1.0
            else:
                weight = -1.5

            # Social feature: did user follow this event's organiser?
            organizer_id = int(event["organizer_id"]) if "organizer_id" in event.index else -1
            organizer_is_followed = 1 if (follows_set and organizer_id in follows_set) else 0

            # Timestamp: after event ends + small noise (when rating is left)
            ts = event["start_time"] + timedelta(
                hours=float(event["duration_hours"]) + float(rng.random() * 2)
            )

            rows.append({
                "user_id":              int(user["user_id"]),
                "event_id":             int(event["event_id"]),
                "signal_type":          signal_type,
                "rating":               rating,
                "label":                label,
                "implicit_label":       implicit_label,
                "signal_weight":        weight,
                "timestamp":            ts,
                "organizer_is_followed": organizer_is_followed,
            })

    df = pd.DataFrame(rows)
    df.sort_values("timestamp", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


# ── Step 6: Build splits ──────────────────────────────────────────────────────

def build_splits(
    interactions_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns (train_df, test_df, train_implicit_df, cold_df).

    Split strategy — Leave-One-Out per user:
      warm users: last interaction by timestamp → test positive
                  all others                   → train
      cold users: all interactions              → cold evaluation set
    """
    cold_ids  = set(range(N_USERS - N_COLD_USERS, N_USERS))
    warm_mask = ~interactions_df["user_id"].isin(cold_ids)
    warm_df   = interactions_df[warm_mask].copy()
    cold_df   = interactions_df[~warm_mask].copy()

    # Leave last RATED interaction per warm user as the LOO test positive.
    # Using any signal type risks picking a leave event as the "positive", which
    # would corrupt the evaluation; only join_rated rows have a valid relevance label.
    warm_df_sorted = warm_df.sort_values(["user_id", "timestamp"])
    rated_mask  = warm_df_sorted["signal_type"] == "join_rated"
    rated_sorted = warm_df_sorted[rated_mask]
    last_rated_idx = rated_sorted.groupby("user_id").tail(1).index

    test_mask = warm_df_sorted.index.isin(last_rated_idx)
    # Drop users with no rated interaction from test (shouldn't happen at this scale)
    train_df = warm_df_sorted[~test_mask].reset_index(drop=True)
    test_df  = warm_df_sorted[test_mask].reset_index(drop=True)

    # Implicit training set: all positive signals in train (no leave events)
    train_implicit_df = train_df[train_df["implicit_label"] == 1].reset_index(drop=True)

    return train_df, test_df, train_implicit_df, cold_df.reset_index(drop=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    rng     = np.random.default_rng(SEED)
    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(exist_ok=True)

    # Users
    print(f"[1/4] Generating {N_USERS:,} users ...")
    users_df = generate_users(rng)
    users_df.to_csv(out_dir / "users.csv", index=False)
    type_counts = users_df["motivation_type"].value_counts().to_dict()
    freq_counts = users_df["frequency_tier"].value_counts().to_dict()
    print(f"      motivation types: {type_counts}")
    print(f"      frequency tiers:  {freq_counts}")

    # Events
    print(f"[2/4] Generating {N_EVENTS:,} events (24-month window) ...")
    events_df = generate_events(rng)
    events_df.to_csv(out_dir / "events.csv", index=False)

    # Follow network
    print(f"[3/4] Generating follow network ...")
    follows_df = generate_follows(users_df, rng)
    follows_df.to_csv(out_dir / "follows.csv", index=False)
    n_warm = N_USERS - N_COLD_USERS
    print(f"      {len(follows_df):,} follow pairs  "
          f"(avg {len(follows_df)/n_warm:.1f} follows/warm user)")

    # Interactions
    print(f"[4/4] Generating interactions (~{N_USERS * 35:,} expected) ...")
    interactions_df = generate_interactions(users_df, events_df, rng, follows_df=follows_df)
    interactions_df.to_csv(out_dir / "interactions.csv", index=False)

    n_total  = len(interactions_df)
    n_rated  = int((interactions_df["signal_type"] == "join_rated").sum())
    n_imp    = int((interactions_df["signal_type"] == "join_no_rate").sum())
    n_leave  = int((interactions_df["signal_type"] == "leave").sum())
    print(f"      {n_total:,} total rows:")
    print(f"        join_rated    {n_rated:,}  ({n_rated/n_total*100:.1f}%)")
    print(f"        join_no_rate  {n_imp:,}  ({n_imp/n_total*100:.1f}%)")
    print(f"        leave         {n_leave:,}  ({n_leave/n_total*100:.1f}%)")
    rated = interactions_df[interactions_df["signal_type"] == "join_rated"]
    n_pos  = int((rated["label"] == 1).sum())
    print(f"        pos/neg in rated: {n_pos:,}/{len(rated)-n_pos:,}  "
          f"({n_pos/max(len(rated),1)*100:.1f}% positive)")
    print("        rating distribution (rated only):")
    for v, cnt in rated["rating"].value_counts().sort_index().items():
        bar = "#" * (cnt * 30 // max(len(rated), 1))
        print(f"          {int(v)}  {bar}  {cnt:,}")

    # Splits
    print("\n[Splitting: leave-one-out per warm user]")
    train_df, test_df, train_implicit_df, cold_df = build_splits(interactions_df)

    train_df.to_csv(        out_dir / "train.csv",             index=False)
    test_df.to_csv(         out_dir / "test.csv",              index=False)
    train_implicit_df.to_csv(out_dir / "train_implicit.csv",   index=False)
    cold_df.to_csv(         out_dir / "cold_start_users.csv",  index=False)

    print(f"      train.csv               {len(train_df):,}  rows  ({n_warm} warm users, all but last)")
    print(f"      test.csv                {len(test_df):,}   rows  (1 positive per warm user)")
    print(f"      train_implicit.csv      {len(train_implicit_df):,}  rows  (positive implicit only)")
    print(f"      cold_start_users.csv    {len(cold_df):,}  rows  ({N_COLD_USERS} held-out users)")
    print(f"\n      avg interactions / warm user: "
          f"{len(train_df)/n_warm:.1f} train + 1 test")

    print(f"\nDone. All files written to  {out_dir.resolve()}")


if __name__ == "__main__":
    main()
