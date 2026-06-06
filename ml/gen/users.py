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
