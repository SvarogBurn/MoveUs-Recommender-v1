"""Emergent event fields."""
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
