"""LightGBM LambdaMART learning-to-rank over dense pair features."""
import numpy as np
import lightgbm as lgb


class LGBMRankerRec:
    name = "LightGBM-LambdaMART"
    def fit(self, ctx):
        self.fc = ctx.features
        rated = ctx.train[ctx.train["signal_type"] == "join_rated"].copy()
        rated = rated.sort_values("user_id")
        rows = [(int(r.user_id), int(r.event_id)) for r in rated.itertuples(index=False)]
        X = np.array([self.fc.pair_dense(u, np.array([e]))[0] for (u, e) in rows])
        y = rated["rating"].astype(int).values
        groups = rated.groupby("user_id").size().values
        self.model = lgb.LGBMRanker(
            objective="lambdarank", metric="ndcg", n_estimators=200,
            learning_rate=0.05, num_leaves=31, min_child_samples=5, verbose=-1,
        )
        # guard: lambdarank needs label variety; if all-equal, jitter one
        if len(np.unique(y)) < 2 and len(y) > 1:
            y = y.copy(); y[0] = max(0, y[0] - 1)
        self.model.fit(X, y, group=groups)

    def score(self, user_id, candidate_event_ids):
        X = self.fc.pair_dense(int(user_id), np.asarray(candidate_event_ids))
        return self.model.predict(X)
