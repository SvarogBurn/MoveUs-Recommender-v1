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
