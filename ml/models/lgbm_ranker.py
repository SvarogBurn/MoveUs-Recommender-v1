"""LightGBM LambdaMART learning-to-rank over dense pair features.

Each user's rated attendances (graded label) are contrasted against sampled
feasible-but-unattended events (label 0) so the ranker learns to separate
events the user would join from comparable events they would not. Features are
passed as named DataFrames on both fit and predict to keep sklearn from warning
about missing feature names.
"""
from itertools import groupby

import numpy as np
import pandas as pd
import lightgbm as lgb

from ml.models.context import FEATURE_NAMES
from ml.models._sampling import user_feasible_events, sample_negatives


class LGBMRankerRec:
    name = "LightGBM-LambdaMART"

    def __init__(self, neg_per_pos: int = 4, seed: int = 0):
        self.neg_per_pos, self.seed = neg_per_pos, seed

    def fit(self, ctx):
        self.fc = ctx.features
        rated = ctx.train[ctx.train["signal_type"] == "join_rated"]
        pos = [(int(r.user_id), int(r.event_id), int(r.rating))
               for r in rated.itertuples(index=False)]

        attended, pos_users = {}, [u for u, _, _ in pos]
        for u, e, _ in pos:
            attended.setdefault(u, set()).add(e)
        feasible = user_feasible_events(ctx.users, ctx.events, pos_users)
        all_events = ctx.events["event_id"].astype(int).values
        neg = sample_negatives(feasible, attended, pos_users,
                               self.neg_per_pos, all_events, seed=self.seed)

        # labelled rows grouped by user (lambdarank needs contiguous query groups)
        rows = pos + [(u, e, 0) for (u, e) in neg]
        rows.sort(key=lambda t: t[0])
        X = np.array([self.fc.pair_dense(u, np.array([e]))[0] for (u, e, _) in rows])
        y = np.array([lab for (_, _, lab) in rows], dtype=int)
        groups = [sum(1 for _ in g) for _, g in groupby(rows, key=lambda t: t[0])]

        # guard: lambdarank needs label variety; if all-equal, jitter one
        if len(np.unique(y)) < 2 and len(y) > 1:
            y = y.copy(); y[0] = max(0, y[0] - 1)

        self.model = lgb.LGBMRanker(
            objective="lambdarank", metric="ndcg", n_estimators=200,
            learning_rate=0.05, num_leaves=31, min_child_samples=5, verbose=-1,
        )
        self.model.fit(pd.DataFrame(X, columns=FEATURE_NAMES), y, group=groups)

    def score(self, user_id, candidate_event_ids):
        X = self.fc.pair_dense(int(user_id), np.asarray(candidate_event_ids))
        return self.model.predict(pd.DataFrame(X, columns=FEATURE_NAMES))
