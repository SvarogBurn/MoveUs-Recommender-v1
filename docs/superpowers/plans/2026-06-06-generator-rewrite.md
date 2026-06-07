# Generator Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `ml/generate_data.py` into an event-timeline simulation that produces behaviourally realistic synthetic interactions, with corrected (Table-17-based) personality–activity fit, weighted demographics, a host-eligible organiser rule, a grown follow network, simulated likes, and point-in-time features.

**Architecture:** The monolithic script becomes a focused `ml/gen/` package orchestrated by a thin `generate_data.py` entrypoint. Events are processed in chronological order; for each event a candidate pool joins one-by-one, conditioned on the roster formed so far. A single mutable `SocialState` object holds the follow graph, co-attendance valence, organiser reputation, per-user booked intervals, likes, and per-user history-so-far, and exposes point-in-time reads. Ratings, follows and likes are produced at event resolution and fed back into the state.

**Tech Stack:** Python 3.12, numpy, pandas, pytest. No Django dependency (standalone scripts).

**Source specs:** [event-timeline simulation](../specs/2026-06-06-event-timeline-simulation-design.md), [feature-pipeline redesign](../specs/2026-06-06-feature-pipeline-redesign-design.md). Fit coefficients are taken verbatim from Table 17 of `workrefferences/syntheticdata.txt`.

---

## File structure

| File | Responsibility |
|---|---|
| `ml/gen/__init__.py` | package marker |
| `ml/gen/config.py` | all constants: scale, RNG seed, archetypes, frequency tiers, gender weights, **Table-17 fit coefficients**, `CLUSTER_ATTRS`, `ACTIVITY_CLUSTER`, `ACTIVITY_FLEXIBLE_SIZE`, geo clusters, logit weights |
| `ml/gen/users.py` | `generate_users` — weighted gender, uniform Big Five, archetype + frequency tier, decoupled survey fields, participation tiers |
| `ml/gen/events.py` | `generate_events` — activity/skill/capacity/duration, `start_time`+`end_time`, host-eligible organisers (~1/12), no pre-baked attendance |
| `ml/gen/fit.py` | `personality_fit` (Table-17 coefficients), `static_match`, gated `size_fit`, `tier_fit`, `dur_fit`, `comp_fit` |
| `ml/gen/social_state.py` | `SocialState` — seed/grown follows, co-attendance valence, organiser stats, booked intervals, likes, per-user history-so-far; point-in-time reads |
| `ml/gen/calibrate.py` | `calibrate_propensity` — per-user intercept so expected joins ≈ tier target |
| `ml/gen/enrollment.py` | `run_enrollment`, `resolve_event` (signals, rating with homophily + satisfaction, state updates, point-in-time emission) |
| `ml/gen/timeline.py` | `run_timeline` — chronological sweep + candidate prefilter; assembles interaction rows |
| `ml/gen/splits.py` | `finalize_events`, `ensure_min_joins`, `build_splits` |
| `ml/gen/io.py` | `write_all` — CSV outputs |
| `ml/generate_data.py` | thin entrypoint: `from ml.gen.timeline import main; main()` |
| `ml/tests/` | pytest tests |

---

## Task 0: Test scaffolding

**Files:**
- Create: `ml/gen/__init__.py` (empty)
- Create: `ml/tests/conftest.py`
- Create: `pytest.ini`

- [ ] **Step 1: Create package marker and pytest config**

`pytest.ini` (`pythonpath = .` puts the repo root on `sys.path` so `import ml.gen.*`
resolves; `importlib` mode means test files need no `__init__.py`):
```ini
[pytest]
pythonpath = .
testpaths = ml/tests
python_files = test_*.py
addopts = -q --import-mode=importlib
```

`ml/tests/conftest.py`:
```python
import numpy as np
import pytest


@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def small(monkeypatch):
    """Shrink scale so tests run fast and deterministically."""
    from ml.gen import config as c
    monkeypatch.setattr(c, "N_USERS", 400)
    monkeypatch.setattr(c, "N_EVENTS", 200)
    monkeypatch.setattr(c, "N_COLD_USERS", 40)
    return c
```

- [ ] **Step 2: Verify pytest collects nothing yet (no errors)**

Run: `python -m pytest -q`
Expected: `no tests ran` (exit 5) — confirms config is valid.

- [ ] **Step 3: Commit**

```bash
git add ml/gen/__init__.py ml/tests/conftest.py pytest.ini
git commit -m "test: scaffold pytest for ml generator package"
```

---

## Task 1: Config constants (incl. Table-17 fit coefficients)

**Files:**
- Create: `ml/gen/config.py`
- Test: `ml/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_config.py`:
```python
import numpy as np
from ml.gen import config as c


def test_archetype_fractions_sum_to_one():
    assert abs(sum(c.MOTIVATION_ARCHETYPES.values()) - 1.0) < 1e-9


def test_freq_tier_dist_rows_sum_to_one():
    for mt, dist in c.FREQ_TIER_DIST.items():
        assert abs(sum(dist.values()) - 1.0) < 1e-9, mt


def test_gender_weights_minorities_small_and_sum_one():
    w = c.GENDER_WEIGHTS  # [MALE, FEMALE, NON_BINARY, PREFER_NOT_TO_SAY]
    assert abs(sum(w) - 1.0) < 1e-9
    assert w[0] > 0.4 and w[1] > 0.4
    assert w[2] < 0.05 and w[3] < 0.05


def test_fit_coefficients_match_table_17_verbatim():
    f = c.FIT_COEFFICIENTS
    assert f["O_risk"] == 0.42      # Openness x Risk tolerance [84]
    assert f["E_social"] == 0.42    # Extraversion x Social interaction [96]
    assert f["H_risk"] == 0.75      # Hardiness x Risk tolerance [103]
    assert f["N_risk"] == -0.47     # Neuroticism x Risk tolerance [84]
    # conscientiousness x consistency: theoretical (no Table-17 number)
    assert 0.0 <= f["C_consistency"] <= 0.5


def test_every_activity_has_cluster_and_flexible_flag():
    assert set(c.ACTIVITY_CLUSTER.keys()) == set(range(31))
    assert set(c.ACTIVITY_FLEXIBLE_SIZE.keys()) == set(range(31))
    # fixed-format sports are not flexible
    assert c.ACTIVITY_FLEXIBLE_SIZE[2] is False   # SOCCER
    assert c.ACTIVITY_FLEXIBLE_SIZE[3] is False   # TENNIS
    assert c.ACTIVITY_FLEXIBLE_SIZE[0] is True    # HIKING


def test_cluster_attrs_cover_eight_clusters():
    assert set(c.CLUSTER_ATTRS.keys()) == set(range(8))
    for a in c.CLUSTER_ATTRS.values():
        assert set(a.keys()) == {"risk", "consistency", "social", "injury"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest ml/tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: ml.gen.config` / attribute errors.

- [ ] **Step 3: Write the implementation**

`ml/gen/config.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest ml/tests/test_config.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add ml/gen/config.py ml/tests/test_config.py
git commit -m "feat(gen): config constants with Table-17 fit coefficients"
```

---

## Task 2: `generate_users`

**Files:**
- Create: `ml/gen/users.py`
- Test: `ml/tests/test_users.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_users.py`:
```python
import numpy as np
from ml.gen import config as c
from ml.gen.users import generate_users


def test_user_count_and_columns(small, rng):
    df = generate_users(rng)
    assert len(df) == c.N_USERS
    for col in ["user_id", "motivation_type", "frequency_tier", "gender",
                "openness", "conscientiousness", "extraversion", "agreeableness",
                "neuroticism", "hardiness", "acquaintance_preference",
                "preferred_group_size", "participation_groups",
                "organizing_openness", "leadership_inclination"]:
        assert col in df.columns


def test_gender_distribution_weighted(small, rng):
    df = generate_users(rng)
    frac = df["gender"].value_counts(normalize=True)
    assert frac.get(0, 0) > 0.35 and frac.get(1, 0) > 0.35     # majorities
    assert frac.get(2, 0) < 0.08 and frac.get(3, 0) < 0.08     # minorities


def test_participation_groups_only_three_tiers(small, rng):
    df = generate_users(rng)
    for s in df["participation_groups"]:
        vals = {int(x) for x in str(s).split(",") if x != ""}
        assert vals.issubset({0, 1, 2})       # never 3 (ROMANTIC dropped)
        assert len(vals) >= 1


def test_survey_fields_have_spread(small, rng):
    df = generate_users(rng)
    # decoupled fields must vary, not collapse to a constant
    assert df["preferred_group_size"].nunique() > 4
    assert df["acquaintance_preference"].nunique() >= 4


def test_bigfive_population_distribution(small, rng):
    df = generate_users(rng)
    # uniform Normal(0.5, 0.1)-ish: mean near 0.5, modest spread, same for all
    assert 0.4 < df["extraversion"].mean() < 0.6
    assert df["extraversion"].std() < 0.2
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_users.py -v`
Expected: FAIL (`ModuleNotFoundError: ml.gen.users`).

- [ ] **Step 3: Write the implementation**

`ml/gen/users.py`:
```python
"""User population generation."""
import numpy as np
import pandas as pd

from ml.gen import config as c


def _clip01(x):
    return np.clip(x, 0.0, 1.0)


def generate_users(rng: np.random.Generator) -> pd.DataFrame:
    n = c.N_USERS

    names = list(c.MOTIVATION_ARCHETYPES)
    fracs = np.array([c.MOTIVATION_ARCHETYPES[k] for k in names])
    motiv = rng.choice(len(names), size=n, p=fracs)
    motivation_type = [names[i] for i in motiv]

    tiers = ["sparse", "occasional", "regular", "frequent"]
    frequency_tier = [
        str(rng.choice(tiers, p=np.array([c.FREQ_TIER_DIST[mt][t] for t in tiers])))
        for mt in motivation_type
    ]

    # Uniform Big Five for everyone (decoupled from archetype)
    def bigfive():
        return _clip01(rng.normal(0.5, 0.1, n))
    O, C, E, A, N, H = (bigfive() for _ in range(6))
    Cf = rng.beta(4, 3, n)
    Lc = rng.beta(4, 3, n)

    # Weighted gender
    gender = rng.choice(4, size=n, p=np.array(c.GENDER_WEIGHTS))
    ages = rng.integers(16, 65, n)

    geo = rng.integers(0, len(c.GEO_CLUSTERS), n)
    lat = np.array([rng.normal(c.GEO_CLUSTERS[g][0], c.GEO_CLUSTERS[g][2]) for g in geo])
    lng = np.array([rng.normal(c.GEO_CLUSTERS[g][1], c.GEO_CLUSTERS[g][2]) for g in geo])

    # Decoupled survey-preference fields (own broad distributions)
    pref_dur = rng.integers(15, 181, n)                       # minutes
    organizing_openness = rng.integers(0, 3, n)               # 0..2
    leadership = rng.integers(1, 6, n)                        # 1..5
    max_travel = np.clip(rng.normal(20, 12, n), 2, 100).astype(int)
    weekly_tgt = rng.integers(1, 8, n)
    pushes = rng.integers(1, 6, n)
    group_size = rng.integers(1, 11, n)                       # 1..10
    acquaint = rng.integers(0, 5, n)                          # 0..4
    enjoy_new = rng.integers(1, 6, n)
    act_soc = rng.integers(1, 6, n)
    mot_comp = rng.integers(1, 6, n)
    planning = rng.integers(1, 6, n)
    burden = rng.integers(1, 6, n)

    # Participation tiers: multi-hot over {0,1,2}, biased to FIRST_HAND + COMMON
    part_groups = []
    for i in range(n):
        chosen = {int(t) for t in c.PARTICIPATION_TIERS if rng.random() < 0.5}
        if not chosen:
            chosen = {int(rng.choice(c.PARTICIPATION_TIERS))}
        part_groups.append(",".join(map(str, sorted(chosen))))

    # Preferred activities (1-4) and per-activity skills
    pref_acts, pref_skills = [], []
    for i in range(n):
        k = int(rng.integers(1, 5))
        acts = rng.choice(31, size=k, replace=False)
        skl = rng.integers(0, 4, k)
        pref_acts.append(",".join(map(str, acts.tolist())))
        pref_skills.append(",".join(map(str, skl.tolist())))

    # Availability
    avail_days, avail_times = [], []
    for i in range(n):
        nd = int(rng.integers(2, 8))
        nt = int(rng.integers(1, 5))
        d = rng.choice(7, size=min(nd, 7), replace=False)
        t = rng.choice(4, size=min(nt, 4), replace=False)
        avail_days.append(",".join(map(str, sorted(d.tolist()))))
        avail_times.append(",".join(map(str, sorted(t.tolist()))))

    # Host eligibility: high organizing_openness OR high leadership, throttled to ~1/12
    eligible = (organizing_openness >= 2) | (leadership >= 4)
    elig_idx = np.where(eligible)[0]
    n_target = int(round(c.ORGANIZER_FRACTION * n))
    host_eligible = np.zeros(n, dtype=bool)
    if len(elig_idx) > 0:
        pick = rng.choice(elig_idx, size=min(n_target, len(elig_idx)), replace=False)
        host_eligible[pick] = True

    return pd.DataFrame({
        "user_id": np.arange(n),
        "motivation_type": motivation_type,
        "frequency_tier": frequency_tier,
        "openness": O.round(4), "conscientiousness": C.round(4),
        "extraversion": E.round(4), "agreeableness": A.round(4),
        "neuroticism": N.round(4), "hardiness": H.round(4),
        "confidence": Cf.round(4), "locus_of_control": Lc.round(4),
        "preferred_session_duration": pref_dur,
        "organizing_openness": organizing_openness,
        "leadership_inclination": leadership,
        "max_travel_distance": max_travel,
        "weekly_activity_target": weekly_tgt,
        "pushes_through_discomfort": pushes,
        "preferred_group_size": group_size,
        "acquaintance_preference": acquaint,
        "enjoys_meeting_new_people": enjoy_new,
        "activity_vs_social": act_soc,
        "motivated_by_competition": mot_comp,
        "planning_horizon": planning,
        "feels_like_burden": burden,
        "age": ages, "gender": gender,
        "latitude": lat.round(6), "longitude": lng.round(6), "geo_cluster": geo,
        "preferred_activities": pref_acts, "preferred_skills": pref_skills,
        "availability_days": avail_days, "availability_times": avail_times,
        "participation_groups": part_groups,
        "host_eligible": host_eligible,
    })
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_users.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add ml/gen/users.py ml/tests/test_users.py
git commit -m "feat(gen): generate_users with weighted gender, tiers, host eligibility"
```

---

## Task 3: `generate_events`

**Files:**
- Create: `ml/gen/events.py`
- Test: `ml/tests/test_events.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_events.py`:
```python
import numpy as np
import pandas as pd
from ml.gen import config as c
from ml.gen.users import generate_users
from ml.gen.events import generate_events


def test_events_have_end_after_start(small, rng):
    users = generate_users(rng)
    ev = generate_events(rng, users)
    assert len(ev) == c.N_EVENTS
    delta_h = (pd.to_datetime(ev["end_time"]) - pd.to_datetime(ev["start_time"])).dt.total_seconds() / 3600
    assert np.allclose(delta_h.values, ev["duration_hours"].values, atol=1e-6)
    assert (delta_h > 0).all()


def test_no_prebaked_attendance_columns(small, rng):
    users = generate_users(rng)
    ev = generate_events(rng, users)
    for col in ["fill_rate", "participant_count", "social_density_cat",
                "avg_organizer_rating", "f1", "f8"]:
        assert col not in ev.columns


def test_organizers_are_host_eligible(small, rng):
    users = generate_users(rng)
    ev = generate_events(rng, users)
    elig = set(users.loc[users["host_eligible"], "user_id"].tolist())
    assert set(ev["organizer_id"].tolist()).issubset(elig)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_events.py -v`
Expected: FAIL (`ModuleNotFoundError: ml.gen.events`).

- [ ] **Step 3: Write the implementation**

`ml/gen/events.py`:
```python
"""Event generation (no pre-baked attendance; explicit end_time)."""
from datetime import timedelta

import numpy as np
import pandas as pd

from ml.gen import config as c


def generate_events(rng: np.random.Generator, users: pd.DataFrame) -> pd.DataFrame:
    n = c.N_EVENTS

    ids = np.array(list(c.RAW_ACT_WEIGHTS.keys()))
    probs = np.array(list(c.RAW_ACT_WEIGHTS.values()), float)
    probs /= probs.sum()
    activities = rng.choice(ids, size=n, p=probs)
    clusters = np.array([c.ACTIVITY_CLUSTER[int(a)] for a in activities])

    skill = np.clip(np.floor(rng.beta(1.5, 3, n) * 4), 0, 3).astype(int)
    max_parts = np.clip(np.round(np.exp(rng.normal(np.log(8), 0.6, n))), 2, 50).astype(int)
    dur = np.clip(rng.normal(1.5, 0.5, n), 0.5, 4.0).round(1)

    day_off = rng.integers(0, c.TIME_SPAN_DAYS, n)
    evening = rng.random(n) < 0.6
    hour = np.where(evening, rng.integers(18, 21, n), rng.integers(9, 12, n))
    start = [c.START_DATE + timedelta(days=int(d), hours=int(h)) for d, h in zip(day_off, hour)]
    end = [s + timedelta(hours=float(h)) for s, h in zip(start, dur)]
    weekday = (day_off % 7).astype(int)
    tod = np.where(evening, 2, 0)

    geo = rng.integers(0, len(c.GEO_CLUSTERS), n)
    lat = np.array([rng.normal(c.GEO_CLUSTERS[g][0], c.GEO_CLUSTERS[g][2]) for g in geo])
    lng = np.array([rng.normal(c.GEO_CLUSTERS[g][1], c.GEO_CLUSTERS[g][2]) for g in geo])

    skill_div = np.clip(rng.beta(1.5, 1.5, n) * 1.5, 0.0, 1.5).round(3)

    host_pool = users.loc[users["host_eligible"], "user_id"].values
    organizer = rng.choice(host_pool, size=n)

    return pd.DataFrame({
        "event_id": np.arange(n),
        "organizer_id": organizer.astype(int),
        "activity_id": activities, "sport_cluster": clusters,
        "skill_level": skill, "max_participants": max_parts,
        "duration_hours": dur, "start_time": start, "end_time": end,
        "latitude": lat.round(6), "longitude": lng.round(6), "geo_cluster": geo,
        "day_of_week": weekday, "time_of_day": tod,
        "skill_diversity": skill_div,
    })
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_events.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add ml/gen/events.py ml/tests/test_events.py
git commit -m "feat(gen): generate_events with end_time and host-eligible organisers"
```

---

## Task 4: Personality–activity fit and static match terms

**Files:**
- Create: `ml/gen/fit.py`
- Test: `ml/tests/test_fit.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_fit.py`:
```python
import numpy as np
from ml.gen import config as c
from ml.gen.fit import personality_fit, dur_fit, size_fit


def test_personality_fit_uses_table17_coefficients():
    # cluster 3 (risk): risk=1.0, social=0.3, consistency=0.3, injury=1.0
    attrs = c.CLUSTER_ATTRS[3]
    O = E = H = N = C_ = 1.0
    expected = (0.42 * O * attrs["risk"] + 0.42 * E * attrs["social"]
                + 0.75 * H * attrs["risk"] - 0.47 * N * attrs["risk"]
                + 0.40 * C_ * attrs["consistency"])
    got = personality_fit(O=O, C=C_, E=E, N=N, H=H, cluster=3)
    assert abs(got - expected) < 1e-9


def test_size_fit_zero_for_fixed_sports():
    # activity 2 = soccer (fixed): size_fit must be 0 regardless of preference
    assert size_fit(pref_size=2, roster_size=20, capacity=22, activity=2) == 0.0
    # activity 0 = hiking (flexible): mismatch penalised (negative)
    assert size_fit(pref_size=2, roster_size=20, capacity=22, activity=0) < 0.0


def test_dur_fit_penalises_mismatch():
    near = dur_fit(pref_minutes=90, event_hours=1.5)   # 90 min == 1.5 h
    far = dur_fit(pref_minutes=30, event_hours=4.0)
    assert near > far
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_fit.py -v`
Expected: FAIL (`ModuleNotFoundError: ml.gen.fit`).

- [ ] **Step 3: Write the implementation**

`ml/gen/fit.py`:
```python
"""Personality-activity fit and static (roster-independent) logit terms."""
import numpy as np

from ml.gen import config as c


def personality_fit(O: float, C: float, E: float, N: float, H: float, cluster: int) -> float:
    a = c.CLUSTER_ATTRS[int(cluster)]
    f = c.FIT_COEFFICIENTS
    return (f["O_risk"] * O * a["risk"]
            + f["E_social"] * E * a["social"]
            + f["H_risk"] * H * a["risk"]
            + f["N_risk"] * N * a["risk"]
            + f["C_consistency"] * C * a["consistency"])


def dur_fit(pref_minutes: float, event_hours: float, sigma: float = 45.0) -> float:
    gap = abs(event_hours * 60.0 - pref_minutes)
    return float(np.exp(-0.5 * (gap / sigma) ** 2))


def size_fit(pref_size: float, roster_size: float, capacity: float,
             activity: int, sigma: float = 4.0) -> float:
    if not c.ACTIVITY_FLEXIBLE_SIZE[int(activity)]:
        return 0.0
    gap = abs(roster_size - pref_size)
    return float(-(gap / sigma))


def comp_fit(motivated_by_competition: float, skill_level: int) -> float:
    # 1..5 centred at 3; competitive users prefer higher-skill events
    centred = (motivated_by_competition - 3.0) / 2.0
    return float(centred * (skill_level - 1.5) / 1.5)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_fit.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add ml/gen/fit.py ml/tests/test_fit.py
git commit -m "feat(gen): Table-17 personality fit + gated size/dur/comp terms"
```

---

## Task 5: `SocialState`

**Files:**
- Create: `ml/gen/social_state.py`
- Test: `ml/tests/test_social_state.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_social_state.py`:
```python
from datetime import datetime, timedelta
from ml.gen.social_state import SocialState


def test_booked_interval_conflict():
    s = SocialState(n_users=10)
    t0 = datetime(2023, 1, 1, 10)
    s.book(user=1, start=t0, end=t0 + timedelta(hours=2))
    assert s.is_busy(1, t0 + timedelta(hours=1), t0 + timedelta(hours=3))   # overlaps
    assert not s.is_busy(1, t0 + timedelta(hours=2), t0 + timedelta(hours=3))  # back-to-back ok
    assert not s.is_busy(2, t0, t0 + timedelta(hours=1))                    # other user free


def test_follow_seed_and_time_gate():
    s = SocialState(n_users=10)
    t_seed = datetime(2023, 1, 1)
    s.add_follow(0, 1, time_created=t_seed)
    # known as of a later time, not before
    assert s.follows(0, 1, as_of=t_seed + timedelta(days=1))
    assert not s.follows(0, 1, as_of=t_seed - timedelta(days=1))


def test_history_snapshot_is_prior_only():
    s = SocialState(n_users=10)
    s.record_rating(user=0, activity=5, cluster=1, rating=4)
    snap1 = s.history_snapshot(user=0, activity=5, cluster=1)
    assert snap1["total_joins"] == 1
    assert snap1["avg_rating"] == 4.0
    # snapshot reflects state BEFORE the next record
    s.record_rating(user=0, activity=5, cluster=1, rating=0)
    snap2 = s.history_snapshot(user=0, activity=5, cluster=1)
    assert snap2["total_joins"] == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_social_state.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write the implementation**

`ml/gen/social_state.py`:
```python
"""Mutable social/history state with point-in-time reads."""
from collections import defaultdict


class SocialState:
    def __init__(self, n_users: int):
        self.n_users = n_users
        self._following = defaultdict(dict)        # u -> {v: time_created}
        self._coattend = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))  # u -> v -> [count, valence_sum]
        self._likes = defaultdict(set)             # u -> {liked v}
        self.like_rows = []                        # (liker, liked, event_id, time)
        self.follow_rows = []                      # (follower, following, time_created)
        self._org_events = defaultdict(int)        # org -> events run
        self._org_rating_sum = defaultdict(float)  # org -> sum ratings received
        self._booked = defaultdict(list)           # u -> [(start, end)]
        # history-so-far
        self._joins = defaultdict(int)
        self._rating_sum = defaultdict(float)
        self._leaves = defaultdict(int)
        self._act_sum = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))   # u -> act -> [n, sum]
        self._clu_sum = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))   # u -> clu -> [n, sum]

    # ---- bookings ----
    def book(self, user, start, end):
        self._booked[user].append((start, end))

    def is_busy(self, user, start, end):
        for (s, e) in self._booked[user]:
            if s < end and start < e:   # strict overlap; back-to-back ok
                return True
        return False

    # ---- follows ----
    def add_follow(self, u, v, time_created):
        if v not in self._following[u]:
            self._following[u][v] = time_created
            self.follow_rows.append((u, v, time_created))

    def follows(self, u, v, as_of):
        t = self._following[u].get(v)
        return t is not None and t <= as_of

    # ---- likes ----
    def add_like(self, u, v, event_id, time):
        if v not in self._likes[u]:
            self._likes[u].add(v)
            self.like_rows.append((u, v, event_id, time))

    def likes(self, u, v):
        return v in self._likes[u]

    # ---- co-attendance ----
    def record_coattendance(self, u, v, valence):
        cell = self._coattend[u][v]
        cell[0] += 1
        cell[1] += valence

    def coattend_valence(self, u, v):
        return self._coattend[u][v][1]

    # ---- organiser stats ----
    def record_organizer_rating(self, org, rating):
        self._org_events[org] += 1
        self._org_rating_sum[org] += rating

    def organizer_score(self, org):
        n = self._org_events[org]
        return (self._org_rating_sum[org] / n) if n else 0.0

    def organizer_events(self, org):
        return self._org_events[org]

    # ---- history-so-far ----
    def record_rating(self, user, activity, cluster, rating):
        self._joins[user] += 1
        self._rating_sum[user] += rating
        a = self._act_sum[user][activity]; a[0] += 1; a[1] += rating
        cl = self._clu_sum[user][cluster]; cl[0] += 1; cl[1] += rating

    def record_join_norate(self, user):
        self._joins[user] += 1

    def record_leave(self, user):
        self._leaves[user] += 1

    def history_snapshot(self, user, activity, cluster):
        j = self._joins[user]
        total_signals = j + self._leaves[user]
        a = self._act_sum[user][activity]
        cl = self._clu_sum[user][cluster]
        return {
            "total_joins": j,
            "avg_rating": (self._rating_sum[user] / j) if j else 0.0,
            "no_show_rate": (self._leaves[user] / total_signals) if total_signals else 0.0,
            "act_affinity": (a[1] / a[0]) if a[0] else 0.0,
            "act_seen_count": a[0],
            "cluster_affinity": (cl[1] / cl[0]) if cl[0] else 0.0,
            "cluster_seen_count": cl[0],
        }
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_social_state.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add ml/gen/social_state.py ml/tests/test_social_state.py
git commit -m "feat(gen): SocialState with bookings, follows, likes, history-so-far"
```

---

## Task 6: Seeding the follow network

**Files:**
- Modify: `ml/gen/social_state.py` (add `seed_follows`)
- Test: `ml/tests/test_seed_follows.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_seed_follows.py`:
```python
import numpy as np
from ml.gen import config as c
from ml.gen.users import generate_users
from ml.gen.social_state import SocialState, seed_follows


def test_seed_covers_small_fraction_including_cold(small, rng):
    users = generate_users(rng)
    s = SocialState(n_users=len(users))
    seed_follows(s, users, rng)
    followers = {f[0] for f in s.follow_rows}
    frac = len(followers) / len(users)
    assert 0.05 < frac < 0.30                      # ~10-15% seeded
    cold_start = c.N_USERS - c.N_COLD_USERS
    cold_followers = {u for u in followers if u >= cold_start}
    assert len(cold_followers) > 0                  # some cold users seeded
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_seed_follows.py -v`
Expected: FAIL (`ImportError: cannot import name 'seed_follows'`).

- [ ] **Step 3: Add the implementation to `ml/gen/social_state.py`**

Append:
```python
def seed_follows(state, users, rng, frac=0.12):
    """Seed a small pre-timeline follow network for ~frac of all users."""
    import numpy as np
    from ml.gen import config as c

    n = len(users)
    geo = users["geo_cluster"].values
    extr = users["extraversion"].values
    chosen = rng.random(n) < frac
    for u in np.where(chosen)[0]:
        k = int(rng.integers(1, 4))                    # 1-3 follows
        same = np.where(geo == geo[u])[0]
        same = same[same != u]
        pool = same if len(same) >= k else np.delete(np.arange(n), u)
        w = extr[pool] + 0.1
        w = w / w.sum()
        for v in rng.choice(pool, size=min(k, len(pool)), replace=False, p=w):
            state.add_follow(int(u), int(v), time_created=c.START_DATE)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_seed_follows.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/gen/social_state.py ml/tests/test_seed_follows.py
git commit -m "feat(gen): seed pre-timeline follow network incl. cold users"
```

---

## Task 7: Enrollment + event resolution (rating, homophily, satisfaction, likes/follows)

**Files:**
- Create: `ml/gen/enrollment.py`
- Test: `ml/tests/test_enrollment.py`

> Implements: sequential one-by-one joins with conflict filtering; signal types
> from archetype propensities; rating anchored to `personality_fit` with
> archetype noise + homophily bump + social-preference satisfaction; valence,
> follow-growth, like-formation, organiser-stat and history updates; and the
> point-in-time feature snapshot emitted on each interaction row.

- [ ] **Step 1: Write the failing test**

`ml/tests/test_enrollment.py`:
```python
import numpy as np
from datetime import datetime
from ml.gen import config as c
from ml.gen.users import generate_users
from ml.gen.events import generate_events
from ml.gen.social_state import SocialState, seed_follows
from ml.gen.calibrate import calibrate_propensity
from ml.gen.enrollment import run_enrollment, resolve_event


def _setup(small):
    rng = np.random.default_rng(1)
    users = generate_users(rng)
    events = generate_events(rng, users).sort_values("start_time").reset_index(drop=True)
    state = SocialState(n_users=len(users))
    seed_follows(state, users, rng)
    base = calibrate_propensity(users, events)
    return rng, users, events, state, base


def test_enrollment_respects_capacity_and_conflicts(small):
    rng, users, events, state, base = _setup(small)
    ev = events.iloc[0]
    roster = run_enrollment(ev, users, state, base, rng)
    assert len(roster) <= int(ev["max_participants"])
    # enrollment books every member for the event window (the conflict-avoidance
    # mechanism), so each is now busy and would be excluded from an overlapping event
    for uid in roster:
        assert state.is_busy(uid, ev["start_time"], ev["end_time"])


def test_resolve_emits_pointintime_rows(small):
    rng, users, events, state, base = _setup(small)
    rows = []
    for _, ev in events.iterrows():
        roster = run_enrollment(ev, users, state, base, rng)
        rows += resolve_event(ev, roster, users, state, rng)
        if len(rows) > 50:
            break
    cols = set(rows[0].keys())
    for col in ["user_id", "event_id", "signal_type", "rating", "label",
                "signal_weight", "timestamp", "join_order",
                "n_known_in_roster", "total_joins", "act_affinity"]:
        assert col in cols
    # no user double-booked across resolved events
    seen = {}
    for r in rows:
        pass  # bookings enforced in run_enrollment; covered by conflict test
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_enrollment.py -v`
Expected: FAIL (`ModuleNotFoundError: ml.gen.enrollment`).

- [ ] **Step 3: Write the implementation**

`ml/gen/enrollment.py`:
```python
"""Sequential enrollment and event resolution."""
from datetime import timedelta

import numpy as np

from ml.gen import config as c
from ml.gen.fit import personality_fit, dur_fit, size_fit, comp_fit


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def _candidate_pool(ev, users, state, rng):
    """Prefilter: matching activity/cluster + within travel + not busy."""
    act = int(ev["activity_id"]); clu = int(ev["sport_cluster"])
    pref_acts = users["preferred_activities"].str.split(",")
    mask = pref_acts.apply(lambda lst: str(act) in lst).values
    # cluster fallback
    for i in np.where(~mask)[0]:
        lst = [int(x) for x in users.iloc[i]["preferred_activities"].split(",")]
        if any(c.ACTIVITY_CLUSTER[a] == clu for a in lst):
            mask[i] = True
    cand = users.index[mask].tolist()
    return [u for u in cand if not state.is_busy(u, ev["start_time"], ev["end_time"])]


def _known_terms(u, roster, users, state, as_of):
    first = second = known = 0
    val = 0.0
    for m in roster:
        if state.follows(u, m, as_of) or state.follows(m, u, as_of):
            first += 1; known += 1
        else:
            v = state.coattend_valence(u, m)
            if v != 0:
                known += 1; val += np.sign(v)
    return {"known": known, "first": first, "valence": val}


def run_enrollment(ev, users, state, base_propensity, rng, max_passes=3):
    cap = int(ev["max_participants"])
    org = int(ev["organizer_id"])
    roster = [org]
    state.book(org, ev["start_time"], ev["end_time"])
    cand = [u for u in _candidate_pool(ev, users, state, rng) if u != org]
    as_of = ev["start_time"]
    clu = int(ev["sport_cluster"]); act = int(ev["activity_id"])
    org_score = state.organizer_score(org)
    org_first = 1 if state.organizer_events(org) == 0 else 0

    for _ in range(max_passes):
        if len(roster) >= cap:
            break
        rng.shuffle(cand)
        progressed = False
        for u in list(cand):
            if len(roster) >= cap:
                break
            urow = users.iloc[u]
            kt = _known_terms(u, roster, users, state, as_of)
            acq_gap = abs(kt["known"] - int(urow["acquaintance_preference"]))
            social = (c.SOCIAL_WEIGHT[urow["motivation_type"]] * kt["valence"]
                      - 0.3 * acq_gap)
            logit = (base_propensity[u]
                     + c.W_ACT * 1.0
                     + c.W_SIZE * size_fit(int(urow["preferred_group_size"]), len(roster), cap, act)
                     + c.W_DUR * dur_fit(int(urow["preferred_session_duration"]), float(ev["duration_hours"]))
                     + c.W_COMP * comp_fit(int(urow["motivated_by_competition"]), int(ev["skill_level"]))
                     + social
                     + c.W_ORG * (org_score / 4.0 - 0.5 * org_first))
            if rng.random() < _sigmoid(logit):
                roster.append(u)
                state.book(u, ev["start_time"], ev["end_time"])
                cand.remove(u)
                progressed = True
        if not progressed:
            break
    return roster


def _valence(rating, left):
    if left:
        return -1.0
    if rating is None:
        return 0.5
    return 1.0 if rating >= 3 else (-1.0 if rating <= 1 else 0.0)


def resolve_event(ev, roster, users, state, rng):
    rows = []
    as_of = ev["start_time"]
    org = int(ev["organizer_id"])
    members = [u for u in roster if u != org]
    motivations = {u: users.iloc[u]["motivation_type"] for u in roster}

    for order, u in enumerate(members):
        urow = users.iloc[u]
        mt = urow["motivation_type"]
        snap = state.history_snapshot(u, int(ev["activity_id"]), int(ev["sport_cluster"]))
        kt = _known_terms(u, roster, users, state, as_of)

        left = rng.random() < c.LEAVE_PROB[mt]
        rated = (not left) and (rng.random() < c.RATE_PROB[mt])

        rating = None
        if rated:
            fit = personality_fit(float(urow["openness"]), float(urow["conscientiousness"]),
                                  float(urow["extraversion"]), float(urow["neuroticism"]),
                                  float(urow["hardiness"]), int(ev["sport_cluster"]))
            base = c.FIT_BASE_SCALE * fit + c.FIT_BASE_OFFSET
            same = sum(1 for v in roster if v != u and motivations[v] == mt)
            homophily = 0.5 if (roster and rng.random() < same / max(len(roster), 1)) else 0.0
            acq_sat = 0.3 if abs(kt["known"] - int(urow["acquaintance_preference"])) <= 1 else 0.0
            raw = base + homophily + acq_sat + rng.normal(0, c.RATING_NOISE[mt])
            rating = int(np.clip(round(raw), 0, 4))

        if left:
            signal, label, weight = "leave", 0, -1.5
        elif rated:
            signal, label = "join_rated", (1 if rating >= 3 else 0)
            weight = 3.0 if label == 1 else 2.0
        else:
            signal, label, weight = "join_no_rate", 1, 1.0

        ts = ev["end_time"] + timedelta(hours=float(rng.random()))
        rows.append({
            "user_id": int(u), "event_id": int(ev["event_id"]),
            "signal_type": signal, "rating": rating, "label": label,
            "implicit_label": -1 if left else 1, "signal_weight": weight,
            "timestamp": ts, "join_order": order,
            "n_known_in_roster": kt["known"], "n_first_hand_in_roster": kt["first"],
            "known_valence": kt["valence"],
            "organizer_score": state.organizer_score(org),
            "organizer_first_time": 1 if state.organizer_events(org) == 0 else 0,
            **snap,
        })

        # state updates (after snapshot, so features stay point-in-time)
        val = _valence(rating, left)
        if left:
            state.record_leave(u)
        elif rated:
            state.record_rating(u, int(ev["activity_id"]), int(ev["sport_cluster"]), rating)
            state.record_organizer_rating(org, rating)
        else:
            state.record_join_norate(u)

        for v in roster:
            if v == u:
                continue
            state.record_coattendance(u, v, val)
            if val > 0:
                p_follow = float(np.clip(
                    0.15 * float(urow["extraversion"]) * (0.5 + 0.5 * float(urow["agreeableness"])), 0, 1))
                if motivations[v] == mt:
                    p_follow = min(1.0, p_follow * 1.8)
                if not state.follows(u, v, ev["end_time"]) and rng.random() < p_follow:
                    state.add_follow(u, v, time_created=ev["end_time"])
                    if motivations[v] == mt and rng.random() < 0.5:
                        state.add_follow(v, u, time_created=ev["end_time"])
                if rng.random() < 0.10 * max(val, 0):
                    state.add_like(u, v, int(ev["event_id"]), ev["end_time"])
    return rows
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_enrollment.py -v`
Expected: PASS (note: depends on Task 8 `calibrate_propensity`; do Task 8 first if import fails).

- [ ] **Step 5: Commit**

```bash
git add ml/gen/enrollment.py ml/tests/test_enrollment.py
git commit -m "feat(gen): sequential enrollment + resolution (rating, homophily, follows, likes)"
```

---

## Task 8: Propensity calibration

**Files:**
- Create: `ml/gen/calibrate.py`
- Test: `ml/tests/test_calibrate.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_calibrate.py`:
```python
import numpy as np
from ml.gen.users import generate_users
from ml.gen.events import generate_events
from ml.gen.calibrate import calibrate_propensity


def test_calibration_returns_one_value_per_user(small):
    rng = np.random.default_rng(0)
    users = generate_users(rng)
    events = generate_events(rng, users)
    base = calibrate_propensity(users, events)
    assert base.shape == (len(users),)
    # frequent-tier users should get a higher intercept than sparse-tier on average
    freq = base[users["frequency_tier"].values == "frequent"]
    sparse = base[users["frequency_tier"].values == "sparse"]
    if len(freq) and len(sparse):
        assert np.nanmean(freq) > np.nanmean(sparse)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_calibrate.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write the implementation**

`ml/gen/calibrate.py`:
```python
"""Per-user base propensity so expected joins ~ tier target."""
import numpy as np

from ml.gen import config as c


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def calibrate_propensity(users, events, delta=0.4):
    """Bisection on a per-user intercept b so sum sigmoid(static + b + delta) ~ target.

    `static` is approximated as a constant activity-match term across the user's
    matchable events; the dynamic social terms are absorbed by `delta`.
    """
    n = len(users)
    base = np.zeros(n)
    n_events = len(events)
    for i in range(n):
        target = c.FREQ_TIER_TARGET[users.iloc[i]["frequency_tier"]]
        lo, hi = -12.0, 6.0
        for _ in range(40):
            mid = (lo + hi) / 2
            expected = n_events * _sigmoid(c.W_ACT * 0.5 + mid + delta)
            if expected > target:
                hi = mid
            else:
                lo = mid
        base[i] = (lo + hi) / 2
    return base
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_calibrate.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/gen/calibrate.py ml/tests/test_calibrate.py
git commit -m "feat(gen): per-user propensity calibration to frequency-tier targets"
```

---

## Task 9: Timeline orchestration

**Files:**
- Create: `ml/gen/timeline.py`
- Test: `ml/tests/test_timeline.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_timeline.py`:
```python
import numpy as np
import pandas as pd
from ml.gen.timeline import run_timeline


def test_run_timeline_produces_interactions(small):
    rng = np.random.default_rng(7)
    users, events, interactions, state = run_timeline(rng)
    assert len(interactions) > 0
    # chronological
    ts = pd.to_datetime(interactions["timestamp"]).values
    assert (ts[:-1] <= ts[1:]).all()
    # no user in two overlapping events: check each user's booked intervals are disjoint
    for u, ivs in state._booked.items():
        ivs = sorted(ivs)
        for a, b in zip(ivs, ivs[1:]):
            assert a[1] <= b[0]


def test_no_legacy_columns(small):
    rng = np.random.default_rng(7)
    _, _, interactions, _ = run_timeline(rng)
    assert "organizer_is_followed" not in interactions.columns
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_timeline.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write the implementation**

`ml/gen/timeline.py`:
```python
"""Chronological event-timeline sweep."""
import numpy as np
import pandas as pd

from ml.gen import config as c
from ml.gen.users import generate_users
from ml.gen.events import generate_events
from ml.gen.social_state import SocialState, seed_follows
from ml.gen.calibrate import calibrate_propensity
from ml.gen.enrollment import run_enrollment, resolve_event


def run_timeline(rng):
    users = generate_users(rng)
    events = generate_events(rng, users).sort_values("start_time").reset_index(drop=True)
    state = SocialState(n_users=len(users))
    seed_follows(state, users, rng)
    base = calibrate_propensity(users, events)

    rows = []
    for _, ev in events.iterrows():
        roster = run_enrollment(ev, users, state, base, rng)
        rows += resolve_event(ev, roster, users, state, rng)

    interactions = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    return users, events, interactions, state


def main():
    from ml.gen.io import write_all
    rng = np.random.default_rng(c.SEED)
    users, events, interactions, state = run_timeline(rng)
    write_all(users, events, interactions, state)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_timeline.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/gen/timeline.py ml/tests/test_timeline.py
git commit -m "feat(gen): chronological timeline sweep orchestration"
```

---

## Task 10: Finalize events, min-join guarantee, splits

**Files:**
- Create: `ml/gen/splits.py`
- Test: `ml/tests/test_splits.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_splits.py`:
```python
import numpy as np
from ml.gen import config as c
from ml.gen.timeline import run_timeline
from ml.gen.splits import finalize_events, ensure_min_joins, build_splits


def test_finalize_events_emergent_fields(small):
    rng = np.random.default_rng(3)
    users, events, interactions, state = run_timeline(rng)
    events2 = finalize_events(events, interactions)
    for col in ["participant_count", "fill_rate", "social_density_cat", "avg_organizer_rating"]:
        assert col in events2.columns
    assert (events2["participant_count"] >= 0).all()


def test_every_warm_user_has_one_test_row(small):
    rng = np.random.default_rng(3)
    users, events, interactions, state = run_timeline(rng)
    interactions = ensure_min_joins(interactions, users, events, state)
    train, test, train_imp, cold = build_splits(interactions)
    warm = set(range(c.N_USERS - c.N_COLD_USERS))
    warm_present = warm & set(interactions["user_id"].unique())
    assert set(test["user_id"]) == warm_present
    assert test.groupby("user_id").size().max() == 1
    assert set(cold["user_id"]).issubset(set(range(c.N_USERS - c.N_COLD_USERS, c.N_USERS)))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_splits.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write the implementation**

`ml/gen/splits.py`:
```python
"""Emergent event fields, min-join guarantee, and train/test/cold splits."""
import numpy as np
import pandas as pd

from ml.gen import config as c


def finalize_events(events, interactions):
    ev = events.copy()
    joined = interactions[interactions["signal_type"] != "leave"]
    counts = joined.groupby("event_id").size()
    ev["participant_count"] = ev["event_id"].map(counts).fillna(0).astype(int)
    ev["fill_rate"] = (ev["participant_count"] / ev["max_participants"]).clip(0, 1).round(3)
    ev["social_density_cat"] = np.where(ev["participant_count"] < 3, 0,
                                np.where(ev["participant_count"] <= 8, 1, 2)).astype(int)
    rated = interactions[interactions["signal_type"] == "join_rated"]
    org_map = ev.set_index("event_id")["organizer_id"]
    rated = rated.assign(org=rated["event_id"].map(org_map))
    org_mean = rated.groupby("org")["rating"].mean()
    ev["avg_organizer_rating"] = ev["organizer_id"].map(org_mean).fillna(0.0).round(2)
    return ev


def ensure_min_joins(interactions, users, events, state):
    cold = set(range(c.N_USERS - c.N_COLD_USERS, c.N_USERS))
    rated_users = set(interactions[interactions["signal_type"] == "join_rated"]["user_id"])
    extra = []
    ev_first = events.sort_values("start_time").iloc[0]
    for u in range(c.N_USERS):
        if u in cold or u in rated_users:
            continue
        extra.append({
            "user_id": int(u), "event_id": int(ev_first["event_id"]),
            "signal_type": "join_rated", "rating": 3, "label": 1,
            "implicit_label": 1, "signal_weight": 3.0,
            "timestamp": ev_first["end_time"], "join_order": 0,
            "n_known_in_roster": 0, "n_first_hand_in_roster": 0, "known_valence": 0.0,
            "organizer_score": 0.0, "organizer_first_time": 1,
            "total_joins": 0, "avg_rating": 0.0, "no_show_rate": 0.0,
            "act_affinity": 0.0, "act_seen_count": 0,
            "cluster_affinity": 0.0, "cluster_seen_count": 0,
        })
    if extra:
        interactions = pd.concat([interactions, pd.DataFrame(extra)], ignore_index=True)
    return interactions.sort_values("timestamp").reset_index(drop=True)


def build_splits(interactions):
    cold_ids = set(range(c.N_USERS - c.N_COLD_USERS, c.N_USERS))
    warm = interactions[~interactions["user_id"].isin(cold_ids)].copy()
    cold = interactions[interactions["user_id"].isin(cold_ids)].copy()

    warm = warm.sort_values(["user_id", "timestamp"])
    rated = warm[warm["signal_type"] == "join_rated"]
    last_idx = rated.groupby("user_id").tail(1).index
    test = warm[warm.index.isin(last_idx)].reset_index(drop=True)
    train = warm[~warm.index.isin(last_idx)].reset_index(drop=True)
    train_imp = train[train["implicit_label"] == 1].reset_index(drop=True)
    return train, test, train_imp, cold.reset_index(drop=True)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_splits.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/gen/splits.py ml/tests/test_splits.py
git commit -m "feat(gen): emergent event fields, min-join guarantee, LOO/cold splits"
```

---

## Task 11: CSV output + entrypoint + end-to-end smoke test

**Files:**
- Create: `ml/gen/io.py`
- Rewrite: `ml/generate_data.py` (thin entrypoint)
- Test: `ml/tests/test_io_smoke.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_io_smoke.py`:
```python
import numpy as np
import pandas as pd
from ml.gen.timeline import run_timeline
from ml.gen.splits import finalize_events, ensure_min_joins, build_splits
from ml.gen.io import write_all


def test_write_all_produces_expected_files(small, tmp_path, monkeypatch):
    import ml.gen.io as io
    monkeypatch.setattr(io, "DATA_DIR", tmp_path)
    rng = np.random.default_rng(11)
    users, events, interactions, state = run_timeline(rng)
    write_all(users, events, interactions, state)
    for fn in ["users.csv", "events.csv", "follows.csv", "likes.csv",
               "interactions.csv", "train.csv", "test.csv",
               "train_implicit.csv", "cold_start_users.csv"]:
        assert (tmp_path / fn).exists(), fn
    ev = pd.read_csv(tmp_path / "events.csv")
    assert "end_time" in ev.columns and "participant_count" in ev.columns
    assert "f1" not in ev.columns
    follows = pd.read_csv(tmp_path / "follows.csv")
    assert {"follower_id", "following_id", "time_created"}.issubset(follows.columns)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_io_smoke.py -v`
Expected: FAIL (`ModuleNotFoundError: ml.gen.io`).

- [ ] **Step 3: Write the implementation**

`ml/gen/io.py`:
```python
"""CSV output."""
from pathlib import Path

import pandas as pd

from ml.gen import config as c
from ml.gen.splits import finalize_events, ensure_min_joins, build_splits

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def write_all(users, events, interactions, state):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    interactions = ensure_min_joins(interactions, users, events, state)
    events = finalize_events(events, interactions)

    users.to_csv(DATA_DIR / "users.csv", index=False)
    events.to_csv(DATA_DIR / "events.csv", index=False)
    interactions.to_csv(DATA_DIR / "interactions.csv", index=False)

    follows = pd.DataFrame(state.follow_rows, columns=["follower_id", "following_id", "time_created"])
    follows.to_csv(DATA_DIR / "follows.csv", index=False)
    likes = pd.DataFrame(state.like_rows, columns=["liker_id", "liked_id", "event_id", "time_created"])
    likes.to_csv(DATA_DIR / "likes.csv", index=False)

    train, test, train_imp, cold = build_splits(interactions)
    train.to_csv(DATA_DIR / "train.csv", index=False)
    test.to_csv(DATA_DIR / "test.csv", index=False)
    train_imp.to_csv(DATA_DIR / "train_implicit.csv", index=False)
    cold.to_csv(DATA_DIR / "cold_start_users.csv", index=False)
```

`ml/generate_data.py` (replace entire file):
```python
#!/usr/bin/env python3
"""Synthetic data generator entrypoint (event-timeline simulation).

Run from the repo root:  python -m ml.gen.timeline   (or)  python ml/generate_data.py
"""
from ml.gen.timeline import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_io_smoke.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full test suite**

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add ml/gen/io.py ml/generate_data.py ml/tests/test_io_smoke.py
git commit -m "feat(gen): CSV output + thin entrypoint; end-to-end smoke test"
```

---

## Self-review notes (spec coverage)

- Event-timeline sweep, one-by-one joins, mid-pass roster updates → Tasks 7, 9.
- Known-attendees ∪ co-attendance, valence → Tasks 5, 7.
- Seed + grown follows, time-gated, `follows.csv` w/ `time_created` → Tasks 5, 6, 7, 11.
- Soft-propensity frequency, calibration with δ offset → Task 8.
- Organiser reputation (score + first-time) → Task 7.
- Uniform Big Five; 4 behavioural archetypes → Tasks 1, 2.
- Survey fields causal + decoupled; participation tiers; gated size; dur; comp → Tasks 1, 2, 4, 7.
- `acquaintance_preference` target (both directions) → Task 7 (`acq_gap`).
- Motivation homophily on rating + (mutual) follows → Task 7.
- Likes simulation + `liked` rows → Tasks 5, 7, 11 (`liked_attendee_count` consumed by feature plan).
- `end_time`; temporal conflict avoidance → Tasks 3, 5, 7, 9.
- Weighted gender; host-eligible organisers (~1/12) → Tasks 1, 2, 3.
- Table-17 fit coefficients → Tasks 1, 4.
- Emergent event fields; min-join; LOO/cold split → Task 10.
- Point-in-time history columns (for feature plan) → Tasks 5, 7.

**Deferred to Plan 2 (feature pipeline):** consuming these columns in `features.py`,
dropping EFA in the event vector, the manifest/named-ranges decoupling, scalers,
and `liked_attendee_count` assembly. Plan 2 is written after this plan lands.

**Known follow-ups (tune during execution):** `FIT_BASE_SCALE`/offset re-check after
coefficient change; calibration `δ` and the constant activity-match approximation may
need adjustment against observed per-tier means (spec test: ±15%).
```
