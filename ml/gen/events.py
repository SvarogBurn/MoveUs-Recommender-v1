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
