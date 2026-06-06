"""Popularity + feasibility baseline. Candidates are already feasibility-filtered by
the harness; this scores by train popularity, recency, and coarse cluster match.
Also serves as the cold/new-event fallback for ID-only models."""
import numpy as np
import pandas as pd

from ml.models.context import ACTIVITY_CLUSTER


class PopularityRec:
    name = "Popularity"
    def fit(self, ctx):
        self.fc = ctx.features
        self.events = ctx.events.set_index("event_id", drop=False)
        self.users = ctx.users.set_index("user_id", drop=False)
        pop = self.fc.event_pop
        self.maxpop = max(pop.values()) if pop else 1.0
        t = pd.to_datetime(ctx.train["timestamp"])
        self.t0 = t.min() if len(t) else pd.Timestamp("2023-01-01")
        self.span = max((t.max() - self.t0).days, 1) if len(t) else 1

    def _user_clusters(self, uid):
        if uid not in self.users.index:
            return set()
        acts = str(self.users.loc[uid]["preferred_activities"]).split(",")
        return {ACTIVITY_CLUSTER[int(a)] for a in acts if a != ""}

    def score(self, user_id, candidate_event_ids):
        uclu = self._user_clusters(int(user_id))
        out = np.zeros(len(candidate_event_ids))
        for i, e in enumerate(candidate_event_ids):
            e = int(e)
            pop = self.fc.event_pop.get(e, 0.0) / self.maxpop
            ev = self.events.loc[e]
            rec = 1.0 - min(max((pd.to_datetime(ev["start_time"]) - self.t0).days, 0) / self.span, 1.0)
            match = 1.0 if int(ev["sport_cluster"]) in uclu else 0.0
            out[i] = 0.6 * pop + 0.2 * rec + 0.2 * match
        return out
