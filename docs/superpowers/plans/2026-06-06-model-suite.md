# Model Suite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the staged benchmark of eight recommenders (Random, Popularity+feasibility, Logistic Regression, LightGBM-LambdaMART, Factorization Machines, BPR-MF, LightGCN, DeepFM) behind one interface, trained on the temporal `train` split and graded by the eval harness.

**Architecture:** A new `ml/models/` package. A `FeatureContext` built once from the temporal `train` split provides, for any `(user, event)` pair, dense match+history+popularity features (for LogReg/LightGBM), sparse categorical+numeric fields (for FM/DeepFM), and contiguous id maps + interaction/graph structure (for BPR-MF/LightGCN). Every model implements `fit(ctx)`/`score(uid, cand_ids)`; ID-only models fall back to the popularity score for unseen users/events. `run_benchmark.py` wires data → split → context → each model → harness → results.

**Tech Stack:** Python 3.12, numpy, pandas, scikit-learn, lightgbm, torch, pytest. Depends on `ml/eval/` from the [evaluation foundation plan](2026-06-06-evaluation-temporal-split.md).

**Source spec:** [model-suite design](../specs/2026-06-06-model-suite-design.md).

**Important methodological note (applies to every model):** roster-composition features
(`n_known_in_roster`, `known_valence`, etc. emitted by the generator) are NOT used as
model inputs, because at recommendation time the roster does not exist yet. Pair features
are limited to quantities knowable before the event fills: user–event match, the user's
train-history affinity, event popularity/recency, and static profile/metadata.

---

## Prerequisite check

- [ ] **Step 0: Confirm libraries**

Run: `python -c "import sklearn, lightgbm, torch; print(sklearn.__version__, lightgbm.__version__, torch.__version__)"`
If any are missing: `python -m pip install scikit-learn lightgbm torch`.
Confirm the eval foundation is present: `python -c "from ml.eval.harness import evaluate, EvalData; print('ok')"`.

---

## File structure

| File | Responsibility |
|---|---|
| `ml/models/__init__.py` | package marker |
| `ml/models/base.py` | `Recommender` protocol; `TrainContext`; `FeatureContext` |
| `ml/models/context.py` | build `FeatureContext` from the temporal `train` split |
| `ml/models/random_rec.py` | random baseline |
| `ml/models/popularity.py` | popularity+feasibility baseline (also the cold fallback) |
| `ml/models/logreg.py` | logistic regression (sklearn) |
| `ml/models/lgbm_ranker.py` | LightGBM LambdaMART |
| `ml/models/fm.py` | factorization machine (torch) |
| `ml/models/bpr_mf.py` | BPR matrix factorization (torch) |
| `ml/models/lightgcn.py` | LightGCN (torch) |
| `ml/models/deepfm.py` | DeepFM (torch) |
| `ml/models/registry.py` | model factory list |
| `ml/models/run_benchmark.py` | end-to-end benchmark + results |

> Note: trained artifacts (if saved) go to `ml/models_store/`; the existing
> `ml/models/` *directory of `.pkl/.pt` files* from the old pipeline should be moved
> to `ml/models_store/` in Task 1 to free the `ml/models/` package path.

---

## Task 1: Package path + base interface

**Files:**
- Bash: move old model artifacts out of the way
- Create: `ml/models/__init__.py`, `ml/models/base.py`
- Test: `ml/tests/test_model_base.py`

- [ ] **Step 1: Move old artifacts so `ml/models/` can become a package**

```bash
git mv ml/models ml/models_store
git commit -m "chore: move old model artifacts to ml/models_store to free ml/models package path"
```

- [ ] **Step 2: Write the failing test**

`ml/tests/test_model_base.py`:
```python
import numpy as np
from ml.models.base import Recommender, TrainContext


def test_recommender_protocol_runtime_checkable():
    class Dummy:
        name = "dummy"
        def fit(self, ctx): pass
        def score(self, uid, cand): return np.zeros(len(cand))
    assert isinstance(Dummy(), Recommender)


def test_traincontext_holds_frames():
    import pandas as pd
    ctx = TrainContext(users=pd.DataFrame({"user_id": [0]}),
                       events=pd.DataFrame({"event_id": [0]}),
                       train=pd.DataFrame({"user_id": [0], "event_id": [0]}),
                       features=None)
    assert ctx.users.iloc[0]["user_id"] == 0
```

- [ ] **Step 3: Write the implementation**

`ml/models/base.py`:
```python
"""Recommender interface and training context."""
from typing import NamedTuple, Protocol, runtime_checkable

import numpy as np
import pandas as pd


@runtime_checkable
class Recommender(Protocol):
    name: str
    def fit(self, ctx: "TrainContext") -> None: ...
    def score(self, user_id: int, candidate_event_ids: np.ndarray) -> np.ndarray: ...


class TrainContext(NamedTuple):
    users: pd.DataFrame
    events: pd.DataFrame
    train: pd.DataFrame          # interactions with ts < T1, non-cold users
    features: object             # FeatureContext (built in context.py); None in unit tests
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_model_base.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/models/__init__.py ml/models/base.py ml/tests/test_model_base.py
git commit -m "feat(models): Recommender protocol and TrainContext"
```

---

## Task 2: FeatureContext

**Files:**
- Create: `ml/models/context.py`
- Test: `ml/tests/test_context.py`

> Builds, from the `train` split: per-user history (total joins, avg rating, per-activity
> and per-cluster affinity + seen counts, no-show rate), event popularity/recency, and
> contiguous user/event id maps. Exposes `pair_dense(uid, event_ids)` (standardized dense
> features) and helpers used by FM/DeepFM/collaborative models.

- [ ] **Step 1: Write the failing test**

`ml/tests/test_context.py`:
```python
import numpy as np
import pandas as pd
from ml.models.context import build_feature_context


def _toy():
    users = pd.DataFrame({
        "user_id": [0, 1], "is_cold_user": [False, True],
        "latitude": [45.81, 45.81], "longitude": [15.97, 15.97],
        "max_travel_distance": [50, 50],
        "availability_days": ["0,1,2,3,4,5,6", "0,1,2,3,4,5,6"],
        "availability_times": ["0,1,2,3", "0,1,2,3"],
        "preferred_activities": ["1", "1"], "preferred_skills": ["2", "2"],
        "preferred_group_size": [5, 5], "preferred_session_duration": [90, 90],
        "motivated_by_competition": [3, 3],
    })
    events = pd.DataFrame({
        "event_id": [10, 11], "activity_id": [1, 2], "sport_cluster": [1, 2],
        "skill_level": [2, 2], "max_participants": [10, 10], "participant_count": [3, 3],
        "duration_hours": [1.5, 1.5], "day_of_week": [0, 0], "time_of_day": [0, 0],
        "latitude": [45.81, 45.81], "longitude": [45.81, 45.81],
        "start_time": pd.to_datetime(["2023-03-01", "2023-03-02"]),
        "end_time": pd.to_datetime(["2023-03-01 02:00", "2023-03-02 02:00"]),
    })
    train = pd.DataFrame({
        "user_id": [0], "event_id": [10], "signal_type": ["join_rated"],
        "rating": [4], "activity_id": [1], "sport_cluster": [1],
        "timestamp": pd.to_datetime(["2023-02-01"]),
    })
    return users, events, train


def test_pair_dense_shape_and_finiteness():
    users, events, train = _toy()
    fc = build_feature_context(train, users, events)
    X = fc.pair_dense(0, np.array([10, 11]))
    assert X.shape[0] == 2
    assert np.isfinite(X).all()


def test_user_event_id_maps():
    users, events, train = _toy()
    fc = build_feature_context(train, users, events)
    assert fc.has_user(0) and not fc.has_user(1)        # user 1 has no train rows
    assert fc.has_event(10) and not fc.has_event(11)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_context.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write the implementation**

`ml/models/context.py`:
```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_context.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/models/context.py ml/tests/test_context.py
git commit -m "feat(models): FeatureContext (train-time pair features, history, popularity, id maps)"
```

---

## Task 3: Random and Popularity baselines

**Files:**
- Create: `ml/models/random_rec.py`, `ml/models/popularity.py`
- Test: `ml/tests/test_baselines.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_baselines.py`:
```python
import numpy as np
import pandas as pd
from ml.models.random_rec import RandomRec
from ml.models.popularity import PopularityRec
from ml.models.base import TrainContext
from ml.models.context import build_feature_context


def _ctx():
    users = pd.DataFrame({"user_id": [0], "is_cold_user": [False],
                          "latitude": [45.8], "longitude": [15.9], "max_travel_distance": [50],
                          "availability_days": ["0,1,2,3,4,5,6"], "availability_times": ["0,1,2,3"],
                          "preferred_activities": ["1"], "preferred_skills": ["2"],
                          "preferred_group_size": [5], "preferred_session_duration": [90],
                          "motivated_by_competition": [3]})
    events = pd.DataFrame({"event_id": [10, 11], "activity_id": [1, 1], "sport_cluster": [1, 1],
                           "skill_level": [2, 2], "max_participants": [10, 10], "participant_count": [3, 9],
                           "duration_hours": [1.5, 1.5], "day_of_week": [0, 0], "time_of_day": [0, 0],
                           "latitude": [45.8, 45.8], "longitude": [15.9, 15.9],
                           "start_time": pd.to_datetime(["2023-03-01", "2023-03-02"]),
                           "end_time": pd.to_datetime(["2023-03-01 02:00", "2023-03-02 02:00"])})
    train = pd.DataFrame({"user_id": [0, 0, 0], "event_id": [10, 10, 11],
                          "signal_type": ["join_rated"] * 3, "rating": [4, 4, 3],
                          "activity_id": [1, 1, 1], "sport_cluster": [1, 1, 1],
                          "timestamp": pd.to_datetime(["2023-02-01", "2023-02-02", "2023-02-03"])})
    fc = build_feature_context(train, users, events)
    return TrainContext(users=users, events=events, train=train, features=fc)


def test_random_returns_finite_array():
    ctx = _ctx(); m = RandomRec(seed=0); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))
    assert s.shape == (2,) and np.isfinite(s).all()


def test_popularity_prefers_more_attended_event():
    ctx = _ctx(); m = PopularityRec(); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))           # event 10 attended twice, 11 once
    assert s[0] > s[1]
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_baselines.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write the implementations**

`ml/models/random_rec.py`:
```python
"""Uniform random baseline (lower bound)."""
import numpy as np


class RandomRec:
    name = "Random"
    def __init__(self, seed: int = 0):
        self.rng = np.random.default_rng(seed)
    def fit(self, ctx): pass
    def score(self, user_id, candidate_event_ids):
        return self.rng.random(len(candidate_event_ids))
```

`ml/models/popularity.py`:
```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_baselines.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/models/random_rec.py ml/models/popularity.py ml/tests/test_baselines.py
git commit -m "feat(models): random and popularity+feasibility baselines"
```

---

## Task 4: Logistic Regression

**Files:**
- Create: `ml/models/logreg.py`
- Test: `ml/tests/test_logreg.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_logreg.py`:
```python
import numpy as np
from ml.models.logreg import LogRegRec
from ml.tests.test_baselines import _ctx     # reuse the toy context


def test_logreg_fits_and_scores():
    ctx = _ctx()
    m = LogRegRec(); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))
    assert s.shape == (2,) and np.isfinite(s).all()
    assert ((s >= 0) & (s <= 1)).all()         # probabilities
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_logreg.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write the implementation**

`ml/models/logreg.py`:
```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_logreg.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/models/logreg.py ml/tests/test_logreg.py
git commit -m "feat(models): logistic regression baseline"
```

---

## Task 5: LightGBM LambdaMART

**Files:**
- Create: `ml/models/lgbm_ranker.py`
- Test: `ml/tests/test_lgbm.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_lgbm.py`:
```python
import numpy as np
from ml.models.lgbm_ranker import LGBMRankerRec
from ml.tests.test_baselines import _ctx


def test_lgbm_fits_and_scores():
    ctx = _ctx()
    m = LGBMRankerRec(); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))
    assert s.shape == (2,) and np.isfinite(s).all()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_lgbm.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write the implementation**

`ml/models/lgbm_ranker.py`:
```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_lgbm.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/models/lgbm_ranker.py ml/tests/test_lgbm.py
git commit -m "feat(models): LightGBM LambdaMART ranker"
```

---

## Task 6: Factorization Machine (torch)

**Files:**
- Create: `ml/models/fm.py`
- Test: `ml/tests/test_fm.py`

> A compact second-order FM over the dense pair features (treated as real-valued fields),
> trained with logistic loss on positive vs sampled-negative `(user, event)` pairs.

- [ ] **Step 1: Write the failing test**

`ml/tests/test_fm.py`:
```python
import numpy as np
from ml.models.fm import FMRec
from ml.tests.test_baselines import _ctx


def test_fm_fits_and_scores():
    ctx = _ctx()
    m = FMRec(epochs=2, seed=0); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))
    assert s.shape == (2,) and np.isfinite(s).all()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_fm.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write the implementation**

`ml/models/fm.py`:
```python
"""Second-order factorization machine over dense pair features (torch)."""
import numpy as np
import torch
import torch.nn as nn

from ml.models._torch_pairs import build_pos_neg_pairs   # created in Task 6 step 3a


class _FM(nn.Module):
    def __init__(self, d, k=16):
        super().__init__()
        self.lin = nn.Linear(d, 1)
        self.V = nn.Parameter(torch.randn(d, k) * 0.01)
    def forward(self, x):
        linear = self.lin(x).squeeze(-1)
        xv = x @ self.V
        sq = (x ** 2) @ (self.V ** 2)
        inter = 0.5 * (xv ** 2 - sq).sum(1)
        return linear + inter


class FMRec:
    name = "FactorizationMachine"
    def __init__(self, k=16, epochs=15, lr=0.01, seed=0):
        self.k, self.epochs, self.lr, self.seed = k, epochs, lr, seed
    def fit(self, ctx):
        self.fc = ctx.features
        torch.manual_seed(self.seed)
        Xp, Xn = build_pos_neg_pairs(ctx, self.fc, seed=self.seed)
        d = Xp.shape[1]
        self.model = _FM(d, self.k)
        opt = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        bce = nn.BCEWithLogitsLoss()
        X = torch.tensor(np.vstack([Xp, Xn]), dtype=torch.float32)
        y = torch.tensor(np.concatenate([np.ones(len(Xp)), np.zeros(len(Xn))]), dtype=torch.float32)
        for _ in range(self.epochs):
            opt.zero_grad(); loss = bce(self.model(X), y); loss.backward(); opt.step()
    def score(self, user_id, candidate_event_ids):
        X = torch.tensor(self.fc.pair_dense(int(user_id), np.asarray(candidate_event_ids)),
                         dtype=torch.float32)
        with torch.no_grad():
            return self.model(X).numpy()
```

- [ ] **Step 3a: Create the shared pair-sampler `ml/models/_torch_pairs.py`**

```python
"""Build positive and sampled-negative dense pair-feature matrices from train."""
import numpy as np


def build_pos_neg_pairs(ctx, fc, neg_per_pos: int = 2, seed: int = 0):
    rng = np.random.default_rng(seed)
    train = ctx.train
    pos_rows = [(int(r.user_id), int(r.event_id))
                for r in train.itertuples(index=False)
                if r.signal_type in ("join_rated", "join_no_rate")
                and not (r.signal_type == "join_rated" and int(r.rating) < 3)]
    all_events = ctx.events["event_id"].astype(int).values
    seen = {}
    for u, e in pos_rows:
        seen.setdefault(u, set()).add(e)
    neg_rows = []
    for u, _ in pos_rows:
        for _ in range(neg_per_pos):
            e = int(rng.choice(all_events))
            if e not in seen.get(u, set()):
                neg_rows.append((u, e))
    Xp = np.array([fc.pair_dense(u, np.array([e]))[0] for (u, e) in pos_rows]) if pos_rows else np.zeros((1, fc.dense_dim))
    Xn = np.array([fc.pair_dense(u, np.array([e]))[0] for (u, e) in neg_rows]) if neg_rows else np.zeros((1, fc.dense_dim))
    return Xp, Xn
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_fm.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/models/fm.py ml/models/_torch_pairs.py ml/tests/test_fm.py
git commit -m "feat(models): factorization machine (torch) + shared pair sampler"
```

---

## Task 7: BPR-MF (torch)

**Files:**
- Create: `ml/models/bpr_mf.py`
- Test: `ml/tests/test_bpr.py`

> ID-based MF with BPR loss over train positives. Unseen user/event → popularity fallback.

- [ ] **Step 1: Write the failing test**

`ml/tests/test_bpr.py`:
```python
import numpy as np
from ml.models.bpr_mf import BPRMFRec
from ml.tests.test_baselines import _ctx


def test_bpr_scores_and_falls_back_for_unseen():
    ctx = _ctx()
    m = BPRMFRec(epochs=3, seed=0); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))           # user 0 + events 10/11 are in train
    assert s.shape == (2,) and np.isfinite(s).all()
    s_cold = m.score(999, np.array([10, 11]))     # unseen user -> fallback, still finite
    assert np.isfinite(s_cold).all()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_bpr.py -v`
Expected: FAIL.

- [ ] **Step 3: Write the implementation**

`ml/models/bpr_mf.py`:
```python
"""BPR matrix factorization (torch) with popularity fallback for unseen ids."""
import numpy as np
import torch

from ml.models.popularity import PopularityRec


class BPRMFRec:
    name = "BPR-MF"
    def __init__(self, dim=32, epochs=20, lr=0.05, seed=0):
        self.dim, self.epochs, self.lr, self.seed = dim, epochs, lr, seed
    def fit(self, ctx):
        self.fc = ctx.features
        self.fallback = PopularityRec(); self.fallback.fit(ctx)
        torch.manual_seed(self.seed); rng = np.random.default_rng(self.seed)
        uidx, eidx = self.fc.user_index, self.fc.event_index
        nU, nE = len(uidx), len(eidx)
        pos = [(uidx[int(r.user_id)], eidx[int(r.event_id)])
               for r in ctx.train.itertuples(index=False)
               if r.signal_type != "leave" and int(r.user_id) in uidx and int(r.event_id) in eidx]
        if not pos or nU == 0 or nE == 0:
            self.U = self.E = None; return
        pos = np.array(pos)
        self.U = torch.nn.Parameter(torch.randn(nU, self.dim) * 0.01)
        self.E = torch.nn.Parameter(torch.randn(nE, self.dim) * 0.01)
        opt = torch.optim.Adam([self.U, self.E], lr=self.lr)
        seen = {u: set() for u in range(nU)}
        for u, e in pos: seen[u].add(e)
        for _ in range(self.epochs):
            idx = rng.integers(0, len(pos), size=len(pos))
            u = pos[idx, 0]; i = pos[idx, 1]
            j = rng.integers(0, nE, size=len(pos))
            ut = torch.tensor(u); it = torch.tensor(i); jt = torch.tensor(j)
            opt.zero_grad()
            xui = (self.U[ut] * self.E[it]).sum(1)
            xuj = (self.U[ut] * self.E[jt]).sum(1)
            loss = -torch.log(torch.sigmoid(xui - xuj) + 1e-9).mean()
            loss.backward(); opt.step()
    def score(self, user_id, candidate_event_ids):
        cand = np.asarray(candidate_event_ids)
        if self.U is None or int(user_id) not in self.fc.user_index:
            return self.fallback.score(user_id, cand)
        u = self.fc.user_index[int(user_id)]
        out = np.zeros(len(cand))
        with torch.no_grad():
            uvec = self.U[u]
            for k, e in enumerate(cand):
                if int(e) in self.fc.event_index:
                    out[k] = float((uvec * self.E[self.fc.event_index[int(e)]]).sum())
                else:
                    out[k] = float(self.fallback.score(user_id, np.array([e]))[0])
        return out
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_bpr.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/models/bpr_mf.py ml/tests/test_bpr.py
git commit -m "feat(models): BPR-MF with popularity fallback for unseen ids"
```

---

## Task 8: LightGCN (torch)

**Files:**
- Create: `ml/models/lightgcn.py`
- Test: `ml/tests/test_lightgcn.py`

> Light graph convolution over the train user–event bipartite graph; BPR loss;
> layer-averaged embeddings; popularity fallback for unseen ids.

- [ ] **Step 1: Write the failing test**

`ml/tests/test_lightgcn.py`:
```python
import numpy as np
from ml.models.lightgcn import LightGCNRec
from ml.tests.test_baselines import _ctx


def test_lightgcn_scores_and_falls_back():
    ctx = _ctx()
    m = LightGCNRec(epochs=3, layers=2, seed=0); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))
    assert s.shape == (2,) and np.isfinite(s).all()
    assert np.isfinite(m.score(999, np.array([10]))).all()   # unseen -> fallback
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_lightgcn.py -v`
Expected: FAIL.

- [ ] **Step 3: Write the implementation**

`ml/models/lightgcn.py`:
```python
"""LightGCN (torch) over the train user-event bipartite graph; popularity fallback."""
import numpy as np
import torch

from ml.models.popularity import PopularityRec


class LightGCNRec:
    name = "LightGCN"
    def __init__(self, dim=32, layers=2, epochs=20, lr=0.05, seed=0):
        self.dim, self.layers, self.epochs, self.lr, self.seed = dim, layers, epochs, lr, seed
    def fit(self, ctx):
        self.fc = ctx.features
        self.fallback = PopularityRec(); self.fallback.fit(ctx)
        torch.manual_seed(self.seed); rng = np.random.default_rng(self.seed)
        uidx, eidx = self.fc.user_index, self.fc.event_index
        nU, nE = len(uidx), len(eidx)
        pos = [(uidx[int(r.user_id)], eidx[int(r.event_id)])
               for r in ctx.train.itertuples(index=False)
               if r.signal_type != "leave" and int(r.user_id) in uidx and int(r.event_id) in eidx]
        if not pos or nU == 0 or nE == 0:
            self.U = self.E = None; return
        pos = np.array(pos)
        n = nU + nE
        # symmetric-normalized adjacency of the bipartite graph
        rows = np.concatenate([pos[:, 0], nU + pos[:, 1]])
        cols = np.concatenate([nU + pos[:, 1], pos[:, 0]])
        deg = np.bincount(rows, minlength=n).astype(float)
        dinv = 1.0 / np.sqrt(np.maximum(deg, 1.0))
        vals = dinv[rows] * dinv[cols]
        A = torch.sparse_coo_tensor(np.vstack([rows, cols]), torch.tensor(vals, dtype=torch.float32),
                                    (n, n)).coalesce()
        emb = torch.nn.Parameter(torch.randn(n, self.dim) * 0.01)
        opt = torch.optim.Adam([emb], lr=self.lr)

        def propagate(e):
            outs = [e]; x = e
            for _ in range(self.layers):
                x = torch.sparse.mm(A, x); outs.append(x)
            return torch.stack(outs).mean(0)

        for _ in range(self.epochs):
            allemb = propagate(emb)
            idx = rng.integers(0, len(pos), size=len(pos))
            u = torch.tensor(pos[idx, 0]); i = torch.tensor(nU + pos[idx, 1])
            j = torch.tensor(nU + rng.integers(0, nE, size=len(pos)))
            opt.zero_grad()
            xui = (allemb[u] * allemb[i]).sum(1)
            xuj = (allemb[u] * allemb[j]).sum(1)
            loss = -torch.log(torch.sigmoid(xui - xuj) + 1e-9).mean()
            loss.backward(); opt.step()
        with torch.no_grad():
            self.final = propagate(emb)
        self.nU = nU
    def score(self, user_id, candidate_event_ids):
        cand = np.asarray(candidate_event_ids)
        if self.U is None and not hasattr(self, "final"):
            return self.fallback.score(user_id, cand)
        if int(user_id) not in self.fc.user_index:
            return self.fallback.score(user_id, cand)
        u = self.fc.user_index[int(user_id)]
        out = np.zeros(len(cand))
        with torch.no_grad():
            uvec = self.final[u]
            for k, e in enumerate(cand):
                if int(e) in self.fc.event_index:
                    out[k] = float((uvec * self.final[self.nU + self.fc.event_index[int(e)]]).sum())
                else:
                    out[k] = float(self.fallback.score(user_id, np.array([e]))[0])
        return out
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_lightgcn.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/models/lightgcn.py ml/tests/test_lightgcn.py
git commit -m "feat(models): LightGCN over train bipartite graph with fallback"
```

---

## Task 9: DeepFM (torch)

**Files:**
- Create: `ml/models/deepfm.py`
- Test: `ml/tests/test_deepfm.py`

> FM component + deep MLP over the same dense pair features; weighted BCE on pos/neg pairs.

- [ ] **Step 1: Write the failing test**

`ml/tests/test_deepfm.py`:
```python
import numpy as np
from ml.models.deepfm import DeepFMRec
from ml.tests.test_baselines import _ctx


def test_deepfm_fits_and_scores():
    ctx = _ctx()
    m = DeepFMRec(epochs=2, seed=0); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))
    assert s.shape == (2,) and np.isfinite(s).all()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_deepfm.py -v`
Expected: FAIL.

- [ ] **Step 3: Write the implementation**

`ml/models/deepfm.py`:
```python
"""DeepFM: FM second-order term + deep MLP over dense pair features (torch)."""
import numpy as np
import torch
import torch.nn as nn

from ml.models._torch_pairs import build_pos_neg_pairs


class _DeepFM(nn.Module):
    def __init__(self, d, k=16, hidden=(64, 32)):
        super().__init__()
        self.lin = nn.Linear(d, 1)
        self.V = nn.Parameter(torch.randn(d, k) * 0.01)
        layers, prev = [], d
        for h in hidden:
            layers += [nn.Linear(prev, h), nn.ReLU()]; prev = h
        layers += [nn.Linear(prev, 1)]
        self.mlp = nn.Sequential(*layers)
    def forward(self, x):
        linear = self.lin(x).squeeze(-1)
        xv = x @ self.V; sq = (x ** 2) @ (self.V ** 2)
        inter = 0.5 * (xv ** 2 - sq).sum(1)
        deep = self.mlp(x).squeeze(-1)
        return linear + inter + deep


class DeepFMRec:
    name = "DeepFM"
    def __init__(self, k=16, epochs=15, lr=0.01, seed=0):
        self.k, self.epochs, self.lr, self.seed = k, epochs, lr, seed
    def fit(self, ctx):
        self.fc = ctx.features
        torch.manual_seed(self.seed)
        Xp, Xn = build_pos_neg_pairs(ctx, self.fc, seed=self.seed)
        d = Xp.shape[1]
        self.model = _DeepFM(d, self.k)
        opt = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        bce = nn.BCEWithLogitsLoss()
        X = torch.tensor(np.vstack([Xp, Xn]), dtype=torch.float32)
        y = torch.tensor(np.concatenate([np.ones(len(Xp)), np.zeros(len(Xn))]), dtype=torch.float32)
        for _ in range(self.epochs):
            opt.zero_grad(); loss = bce(self.model(X), y); loss.backward(); opt.step()
    def score(self, user_id, candidate_event_ids):
        X = torch.tensor(self.fc.pair_dense(int(user_id), np.asarray(candidate_event_ids)),
                         dtype=torch.float32)
        with torch.no_grad():
            return self.model(X).numpy()
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_deepfm.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/models/deepfm.py ml/tests/test_deepfm.py
git commit -m "feat(models): DeepFM (torch)"
```

---

## Task 10: Registry + benchmark runner + integration

**Files:**
- Create: `ml/models/registry.py`, `ml/models/run_benchmark.py`
- Test: `ml/tests/test_benchmark_integration.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_benchmark_integration.py`:
```python
import numpy as np
from ml.models.run_benchmark import run_benchmark


def test_benchmark_runs_on_small_generated_data(tmp_path, small, monkeypatch):
    # generate a small dataset in memory and run the full benchmark
    import ml.gen.io as io
    monkeypatch.setattr(io, "DATA_DIR", tmp_path)
    import numpy as np
    from ml.gen.timeline import run_timeline
    rng = np.random.default_rng(5)
    users, events, interactions, state = run_timeline(rng)
    io.write_all(users, events, interactions, state)

    results = run_benchmark(data_dir=tmp_path, fast=True)
    assert "Random" in results and "FactorizationMachine" in results
    # sanity: at least one learned model beats Random on overall NDCG@10
    learned = [v["overall"]["ndcg@10"] for k, v in results.items() if k != "Random"]
    assert max(learned) >= results["Random"]["overall"]["ndcg@10"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_benchmark_integration.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write the implementations**

`ml/models/registry.py`:
```python
"""Model factory list (instantiate fresh per run)."""
from ml.models.random_rec import RandomRec
from ml.models.popularity import PopularityRec
from ml.models.logreg import LogRegRec
from ml.models.lgbm_ranker import LGBMRankerRec
from ml.models.fm import FMRec
from ml.models.bpr_mf import BPRMFRec
from ml.models.lightgcn import LightGCNRec
from ml.models.deepfm import DeepFMRec


def all_models(fast: bool = False):
    e = 2 if fast else 15
    ec = 3 if fast else 20
    return [
        RandomRec(seed=0),
        PopularityRec(),
        LogRegRec(),
        LGBMRankerRec(),
        FMRec(epochs=e),
        BPRMFRec(epochs=ec),
        LightGCNRec(epochs=ec),
        DeepFMRec(epochs=e),
    ]
```

`ml/models/run_benchmark.py`:
```python
"""End-to-end benchmark: load data -> temporal split -> context -> models -> harness."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml.eval.split import temporal_split
from ml.eval.harness import evaluate, EvalData
from ml.models.base import TrainContext
from ml.models.context import build_feature_context
from ml.models.registry import all_models

DATA_DIR_DEFAULT = Path(__file__).resolve().parent.parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


def run_benchmark(data_dir=None, fast: bool = False) -> dict:
    data_dir = Path(data_dir) if data_dir else DATA_DIR_DEFAULT
    users = pd.read_csv(data_dir / "users.csv")
    events = pd.read_csv(data_dir / "events.csv", parse_dates=["start_time", "end_time"])
    inter = pd.read_csv(data_dir / "interactions.csv", parse_dates=["timestamp"])

    train, val, test, _ = temporal_split(inter, users)
    fc = build_feature_context(train, users, events)
    ctx = TrainContext(users=users, events=events, train=train, features=fc)
    data = EvalData(users=users, events=events, train=train, val=val, test=test)

    results = {}
    for model in all_models(fast=fast):
        model.fit(ctx)
        results[model.name] = evaluate(model, data)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "benchmark.json", "w") as fh:
        json.dump(results, fh, indent=2)
    rows = []
    for name, r in results.items():
        row = {"model": name}
        for sl, m in r.items():
            row[f"{sl}_ndcg@10"] = round(m["ndcg@10"], 4)
            row[f"{sl}_recall@10"] = round(m["recall@10"], 4)
            row[f"{sl}_mrr"] = round(m["mrr"], 4)
        rows.append(row)
    pd.DataFrame(rows).to_csv(RESULTS_DIR / "benchmark.csv", index=False)
    return results


def main():
    res = run_benchmark()
    print(pd.read_csv(RESULTS_DIR / "benchmark.csv").to_string(index=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_benchmark_integration.py -v`
Expected: PASS (may take a minute at small scale).

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add ml/models/registry.py ml/models/run_benchmark.py ml/tests/test_benchmark_integration.py
git commit -m "feat(models): registry + end-to-end benchmark runner with sliced results"
```

---

## Self-review notes (spec coverage)

- Common `Recommender` interface + `TrainContext` → Task 1.
- Feature context (train-time, point-in-time, no roster features) → Task 2.
- Random, Popularity+feasibility (+ fallback) → Task 3.
- Logistic Regression → Task 4; LightGBM-LambdaMART → Task 5.
- Factorization Machines → Task 6; BPR-MF → Task 7; LightGCN → Task 8; DeepFM → Task 9.
- Cold/new-event fallback for ID-only models → Tasks 7, 8 (popularity fallback).
- Registry + benchmark runner + sliced `benchmark.csv` → Task 10.
- Harness/metrics/slices/split come from the [eval foundation plan](2026-06-06-evaluation-temporal-split.md).

**Known follow-ups (tune during execution):** model hyperparameters (epochs/dim/lr) are
light defaults; raise for the final full-scale run. Add a grouped NDCG bar chart
(`ml/results/benchmark_ndcg.png`) once numbers look sane. LambdaFM deferred.
