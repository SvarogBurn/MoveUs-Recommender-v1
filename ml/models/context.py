"""Feature context built from the temporal train split (point-in-time, no leakage)."""
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

ACTIVITY_CLUSTER = {
    0: 1, 1: 1, 2: 0, 3: 2, 4: 6, 5: 5, 6: 2, 7: 0, 8: 0, 9: 1, 10: 4, 11: 3, 12: 0,
    13: 6, 14: 5, 15: 0, 16: 2, 17: 0, 18: 7, 19: 4, 20: 5, 21: 0, 22: 7, 23: 3,
    24: 3, 25: 3, 26: 7, 27: 7, 28: 0, 29: 1, 30: 5,
}


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1); dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


class FeatureContext:
    def __init__(self, users, events, dense_dim, scaler,
                 user_hist, event_pop, user_index, event_index):
        self.users = users.set_index("user_id", drop=False)
        self.events = events.set_index("event_id", drop=False)
        self.dense_dim = dense_dim
        self.scaler = scaler
        self.user_hist = user_hist        # uid -> dict of history scalars/maps
        self.event_pop = event_pop        # eid -> popularity (train attendance count)
        self.user_index = user_index      # uid -> contiguous idx (train users)
        self.event_index = event_index    # eid -> contiguous idx (train events)

    def has_user(self, uid): return int(uid) in self.user_index
    def has_event(self, eid): return int(eid) in self.event_index

    def _raw_pair(self, uid, eid):
        u = self.users.loc[uid]; e = self.events.loc[eid]
        h = self.user_hist.get(int(uid), {})
        pref_acts = set(int(x) for x in str(u["preferred_activities"]).split(","))
        act = int(e["activity_id"]); clu = int(e["sport_cluster"])
        act_match = 1.0 if act in pref_acts else (0.6 if clu in {ACTIVITY_CLUSTER[a] for a in pref_acts} else 0.1)
        dist = _haversine_km(float(u["latitude"]), float(u["longitude"]),
                             float(e["latitude"]), float(e["longitude"]))
        dist_score = float(np.exp(-dist / max(float(u["max_travel_distance"]), 1.0)))
        avail = (e["day_of_week"] in set(int(x) for x in str(u["availability_days"]).split(","))
                 and e["time_of_day"] in set(int(x) for x in str(u["availability_times"]).split(",")))
        dur_gap = abs(float(e["duration_hours"]) * 60 - float(u["preferred_session_duration"]))
        size_gap = abs(float(e["max_participants"]) - float(u["preferred_group_size"]))
        act_aff = h.get("act_aff", {}).get(act, 0.0)
        act_seen = h.get("act_seen", {}).get(act, 0)
        clu_aff = h.get("clu_aff", {}).get(clu, 0.0)
        clu_seen = h.get("clu_seen", {}).get(clu, 0)
        return [
            act_match, dist_score, float(avail), dur_gap, size_gap,
            float(e["skill_level"]), float(u["motivated_by_competition"]),
            h.get("total_joins", 0.0), h.get("avg_rating", 0.0), h.get("no_show", 0.0),
            act_aff, float(act_seen), clu_aff, float(clu_seen),
            float(self.event_pop.get(int(eid), 0.0)),
        ]

    def pair_dense(self, uid, event_ids):
        raw = np.array([self._raw_pair(int(uid), int(e)) for e in event_ids], dtype=float)
        return self.scaler.transform(raw)


def build_feature_context(train, users, events):
    # per-user history from train
    user_hist = {}
    rated = train[train["signal_type"] == "join_rated"]
    for uid, grp in train.groupby("user_id"):
        rg = grp[grp["signal_type"] == "join_rated"]
        act_aff, act_seen, clu_aff, clu_seen = {}, {}, {}, {}
        for act, ag in rg.groupby("activity_id"):
            act_aff[int(act)] = float(ag["rating"].mean()); act_seen[int(act)] = int(len(ag))
        for clu, cg in rg.groupby("sport_cluster"):
            clu_aff[int(clu)] = float(cg["rating"].mean()); clu_seen[int(clu)] = int(len(cg))
        n_leave = int((grp["signal_type"] == "leave").sum())
        user_hist[int(uid)] = {
            "total_joins": float(len(rg)),
            "avg_rating": float(rg["rating"].mean()) if len(rg) else 0.0,
            "no_show": n_leave / max(len(grp), 1),
            "act_aff": act_aff, "act_seen": act_seen, "clu_aff": clu_aff, "clu_seen": clu_seen,
        }
    event_pop = train[train["signal_type"] != "leave"].groupby("event_id").size().to_dict()
    event_pop = {int(k): float(v) for k, v in event_pop.items()}

    user_index = {int(u): i for i, u in enumerate(sorted(train["user_id"].unique()))}
    event_index = {int(e): i for i, e in enumerate(sorted(train["event_id"].unique()))}

    fc = FeatureContext(users, events, dense_dim=15, scaler=StandardScaler(),
                        user_hist=user_hist, event_pop=event_pop,
                        user_index=user_index, event_index=event_index)
    # fit the scaler on raw train pair features (positive interactions)
    sample = train[train["signal_type"] != "leave"].head(50000)
    raw = np.array([fc._raw_pair(int(r.user_id), int(r.event_id))
                    for r in sample.itertuples(index=False)], dtype=float)
    if len(raw) == 0:
        raw = np.zeros((1, fc.dense_dim))
    fc.scaler.fit(raw)
    return fc
