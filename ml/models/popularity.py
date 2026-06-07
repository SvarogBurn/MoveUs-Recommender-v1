"""Popularity + feasibility baseline. Candidates are already feasibility-filtered by
the harness; this scores by popularity and coarse compatibility.

Popularity is keyed primarily on the event's *activity* (a recurring node), so the
baseline still ranks brand-new events sensibly; event-level attendance is kept as a
secondary signal for events that were seen in training. Also serves as the
cold/unseen fallback for the collaborative models."""
import numpy as np
import pandas as pd

from ml.models.context import ACTIVITY_CLUSTER


class PopularityRec:
    name = "Popularity"

    def fit(self, ctx):
        self.fc = ctx.features
        self.events = ctx.events.set_index("event_id", drop=False)
        self.users = ctx.users.set_index("user_id", drop=False)
        attended = ctx.train[ctx.train["signal_type"] != "leave"]
        if "activity_id" in attended.columns:
            ap = attended.groupby("activity_id").size().to_dict()
        else:
            ap = {}
        self.act_pop = {int(k): float(v) for k, v in ap.items()}
        self.max_act = max(self.act_pop.values()) if self.act_pop else 1.0
        self.event_pop = self.fc.event_pop
        self.maxpop = max(self.event_pop.values()) if self.event_pop else 1.0

    def _user_clusters(self, uid):
        if uid not in self.users.index:
            return set()
        acts = str(self.users.loc[uid]["preferred_activities"]).split(",")
        return {ACTIVITY_CLUSTER[int(a)] for a in acts if a != ""}

    def score(self, user_id, candidate_event_ids):
        uclu = self._user_clusters(int(user_id))
        out = np.zeros(len(candidate_event_ids))
        for i, e in enumerate(candidate_event_ids):
            e = int(e); ev = self.events.loc[e]
            apop = self.act_pop.get(int(ev["activity_id"]), 0.0) / self.max_act
            epop = self.event_pop.get(e, 0.0) / self.maxpop
            match = 1.0 if int(ev["sport_cluster"]) in uclu else 0.0
            out[i] = 0.5 * apop + 0.3 * epop + 0.2 * match
        return out
