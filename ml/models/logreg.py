"""Pointwise logistic regression over dense pair features."""
import numpy as np
from sklearn.linear_model import LogisticRegression

from ml.models.context import build_feature_context  # noqa: F401 (paths consistent)


class LogRegRec:
    name = "LogisticRegression"
    def fit(self, ctx):
        self.fc = ctx.features
        train = ctx.train
        pos = train[train["signal_type"].isin(["join_rated", "join_no_rate"])]
        # positives: rating >= 3 or unrated positive; negatives: leaves + sampled non-pos
        rows, labels = [], []
        for r in train.itertuples(index=False):
            uid, eid = int(r.user_id), int(r.event_id)
            if r.signal_type == "leave":
                rows.append((uid, eid)); labels.append(0)
            elif r.signal_type == "join_rated":
                rows.append((uid, eid)); labels.append(1 if int(r.rating) >= 3 else 0)
            else:
                rows.append((uid, eid)); labels.append(1)
        X = np.array([self.fc.pair_dense(u, np.array([e]))[0] for (u, e) in rows])
        y = np.array(labels)
        if len(np.unique(y)) < 2:           # guard degenerate toy data
            y[0] = 1 - y[0]
        self.clf = LogisticRegression(max_iter=1000).fit(X, y)

    def score(self, user_id, candidate_event_ids):
        X = self.fc.pair_dense(int(user_id), np.asarray(candidate_event_ids))
        return self.clf.predict_proba(X)[:, 1]
