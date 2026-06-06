# Evaluation & Temporal-Split Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the shared evaluation substrate — a global temporal split, full-catalog feasible candidates, Weighted NDCG@10 / Recall@10 with warm/cold/new-event slices — and adjust the generator to emit a flat chronological log plus an `is_cold_user` flag (dropping the LOO split files).

**Architecture:** A new `ml/eval/` package: `metrics` (pure ranking metrics), `split` (temporal partition), `candidates` (per-user relevant + feasible sets), `slices` (warm/cold/new-event classification), `harness` (run a model through the protocol). The generator's LOO split logic is removed; the temporal cut happens in the eval layer from the full `interactions.csv`.

**Tech Stack:** Python 3.12, numpy, pandas, pytest. Builds on the existing `ml/gen/` package and `pytest.ini`.

**Source spec:** [evaluation & temporal-split design](../specs/2026-06-06-evaluation-temporal-split-design.md).

---

## File structure

| File | Responsibility |
|---|---|
| `ml/eval/__init__.py` | package marker |
| `ml/eval/metrics.py` | `ndcg_at_k(scores, rels, k)`, `recall_at_k(scores, rels, k)` |
| `ml/eval/split.py` | `temporal_split(interactions, users, t1q, t2q)` → train/val/test + boundaries |
| `ml/eval/candidates.py` | `relevant_set(u, test_df)`, `feasible_candidates(u, users, events, window)` |
| `ml/eval/slices.py` | `classify_users(...)`, `new_event_ids(...)` |
| `ml/eval/harness.py` | `evaluate(model, ctx)` → results dict |
| `ml/gen/users.py` (modify) | add `is_cold_user` column |
| `ml/gen/splits.py` (modify) | keep `finalize_events`; remove `build_splits`, `ensure_min_joins` |
| `ml/gen/io.py` (modify) | write `is_cold_user`; stop writing train/test/cold split CSVs |
| `ml/gen/timeline.py` (modify) | `main` no longer calls removed split functions |

---

## Task 1: Ranking metrics

**Files:**
- Create: `ml/eval/__init__.py` (empty), `ml/eval/metrics.py`
- Test: `ml/tests/test_metrics.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_metrics.py`:
```python
import numpy as np
from ml.eval.metrics import ndcg_at_k, recall_at_k


def test_ndcg_perfect_ranking():
    # scores already rank the rel=4 item first
    scores = np.array([3.0, 2.0, 1.0])
    rels   = np.array([4,   2,   0])
    assert abs(ndcg_at_k(scores, rels, 10) - 1.0) < 1e-9


def test_ndcg_single_relevant_at_rank_2():
    # index1 (score 2) ranks first with rel 0; index0 (score 1) ranks 2nd with rel 4
    scores = np.array([1.0, 2.0])
    rels   = np.array([4,   0])
    expected = (15.0 / np.log2(3)) / 15.0   # gain(4)=2^4-1=15, discount log2(2+1)
    assert abs(ndcg_at_k(scores, rels, 10) - expected) < 1e-9


def test_ndcg_zero_when_no_relevant():
    assert ndcg_at_k(np.array([1.0, 2.0]), np.array([0, 0]), 10) == 0.0


def test_recall_half():
    scores = np.array([3.0, 2.0, 1.0, 0.0])
    rels   = np.array([1,   0,   1,   0])   # 2 relevant; top-2 contains 1
    assert recall_at_k(scores, rels, 2) == 0.5


def test_recall_all_found():
    scores = np.array([3.0, 2.0, 1.0])
    rels   = np.array([1,   1,   0])
    assert recall_at_k(scores, rels, 10) == 1.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_metrics.py -v`
Expected: FAIL (`ModuleNotFoundError: ml.eval.metrics`).

- [ ] **Step 3: Write the implementation**

`ml/eval/metrics.py`:
```python
"""Ranking metrics with explicit, stated definitions.

Weighted NDCG@k: gain(rel) = 2**rel - 1, discount = log2(rank + 1) (rank 1-indexed).
Recall@k: fraction of relevant items (rel > 0) that appear in the top k.
Ties in `scores` are broken deterministically by original index (stable sort).
"""
import numpy as np


def _topk_order(scores: np.ndarray, k: int) -> np.ndarray:
    # descending by score, stable (ties -> lower index first)
    order = np.argsort(-scores, kind="stable")
    return order[:k]


def ndcg_at_k(scores: np.ndarray, rels: np.ndarray, k: int) -> float:
    scores = np.asarray(scores, dtype=float)
    rels = np.asarray(rels, dtype=float)
    if rels.size == 0 or np.all(rels <= 0):
        return 0.0
    order = _topk_order(scores, k)
    gains = (2.0 ** rels[order]) - 1.0
    discounts = 1.0 / np.log2(np.arange(2, gains.size + 2))
    dcg = float(np.sum(gains * discounts))

    ideal = np.sort(rels)[::-1][:k]
    igains = (2.0 ** ideal) - 1.0
    idiscounts = 1.0 / np.log2(np.arange(2, igains.size + 2))
    idcg = float(np.sum(igains * idiscounts))
    return dcg / idcg if idcg > 0 else 0.0


def recall_at_k(scores: np.ndarray, rels: np.ndarray, k: int) -> float:
    rels = np.asarray(rels, dtype=float)
    total = int(np.sum(rels > 0))
    if total == 0:
        return 0.0
    order = _topk_order(np.asarray(scores, dtype=float), k)
    found = int(np.sum(rels[order] > 0))
    return found / total
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_metrics.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add ml/eval/__init__.py ml/eval/metrics.py ml/tests/test_metrics.py
git commit -m "feat(eval): weighted NDCG@k and Recall@k with explicit definitions"
```

---

## Task 2: Temporal split

**Files:**
- Create: `ml/eval/split.py`
- Test: `ml/tests/test_split.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_split.py`:
```python
import numpy as np
import pandas as pd
from ml.eval.split import temporal_split


def _toy():
    users = pd.DataFrame({"user_id": [0, 1, 2], "is_cold_user": [False, False, True]})
    inter = pd.DataFrame({
        "user_id":  [0, 1, 2, 0, 1, 2, 0, 1, 2, 0],
        "event_id": list(range(10)),
        "signal_type": ["join_rated"] * 10,
        "rating": [3] * 10,
        "timestamp": pd.date_range("2023-01-01", periods=10, freq="D"),
    })
    return users, inter


def test_strict_temporal_ordering():
    users, inter = _toy()
    train, val, test, (t1, t2) = temporal_split(inter, users, t1q=0.6, t2q=0.8)
    assert train["timestamp"].max() < val["timestamp"].min()
    assert val["timestamp"].max() < test["timestamp"].min()


def test_cold_users_excluded_from_train():
    users, inter = _toy()
    train, val, test, _ = temporal_split(inter, users, t1q=0.6, t2q=0.8)
    assert 2 not in set(train["user_id"])          # user 2 is cold
    # cold user's later interactions still appear in val/test
    assert 2 in set(val["user_id"]) | set(test["user_id"])


def test_partitions_disjoint_and_complete_for_warm():
    users, inter = _toy()
    train, val, test, _ = temporal_split(inter, users, t1q=0.6, t2q=0.8)
    warm = inter[~inter["user_id"].isin([2])]
    n = len(pd.concat([train, val, test]).drop_duplicates(subset=["user_id", "event_id"]))
    assert n == len(inter.drop_duplicates(subset=["user_id", "event_id"]))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_split.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write the implementation**

`ml/eval/split.py`:
```python
"""Global temporal split of the interaction log.

train = { ts < T1 and not is_cold_user }
val   = { T1 <= ts < T2 }
test  = { ts >= T2 }
Cold users contribute no train rows (profile-only at test time).
"""
import numpy as np
import pandas as pd


def temporal_split(interactions: pd.DataFrame, users: pd.DataFrame,
                   t1q: float = 0.70, t2q: float = 0.85):
    df = interactions.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    t1 = df["timestamp"].quantile(t1q)
    t2 = df["timestamp"].quantile(t2q)

    cold = set(users.loc[users["is_cold_user"], "user_id"].astype(int))
    is_cold = df["user_id"].isin(cold)

    train = df[(df["timestamp"] < t1) & (~is_cold)].reset_index(drop=True)
    val = df[(df["timestamp"] >= t1) & (df["timestamp"] < t2)].reset_index(drop=True)
    test = df[df["timestamp"] >= t2].reset_index(drop=True)
    return train, val, test, (t1, t2)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_split.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add ml/eval/split.py ml/tests/test_split.py
git commit -m "feat(eval): global temporal split with cold-user train exclusion"
```

---

## Task 3: Generator changes (is_cold_user flag; drop LOO splits)

**Files:**
- Modify: `ml/gen/users.py` (add `is_cold_user`)
- Modify: `ml/gen/splits.py` (remove `build_splits`, `ensure_min_joins`; keep `finalize_events`)
- Modify: `ml/gen/io.py` (write `is_cold_user`; stop writing split CSVs)
- Modify: `ml/gen/timeline.py` (`main` no longer calls removed functions)
- Modify: `ml/tests/test_splits.py` (drop tests for removed functions; keep finalize test)
- Test: `ml/tests/test_cold_flag.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_cold_flag.py`:
```python
import numpy as np
from ml.gen import config as c
from ml.gen.users import generate_users


def test_is_cold_user_flag(small, rng):
    df = generate_users(rng)
    assert "is_cold_user" in df.columns
    cold = df[df["is_cold_user"]]["user_id"].tolist()
    assert set(cold) == set(range(c.N_USERS - c.N_COLD_USERS, c.N_USERS))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_cold_flag.py -v`
Expected: FAIL (`is_cold_user` not in columns).

- [ ] **Step 3: Add the flag in `ml/gen/users.py`**

In `generate_users`, just before the `return pd.DataFrame({...})`, add:
```python
    user_ids = np.arange(n)
    is_cold_user = user_ids >= (c.N_USERS - c.N_COLD_USERS)
```
and add to the returned dict (next to `"user_id": np.arange(n),`):
```python
        "is_cold_user": is_cold_user,
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_cold_flag.py -v`
Expected: PASS.

- [ ] **Step 5: Remove LOO split logic**

In `ml/gen/splits.py` delete the `build_splits` and `ensure_min_joins` functions entirely (keep `finalize_events` and its imports).

In `ml/gen/io.py`, replace the body of `write_all` so it no longer calls `ensure_min_joins`/`build_splits` and no longer writes `train.csv`/`test.csv`/`train_implicit.csv`/`cold_start_users.csv`:
```python
def write_all(users, events, interactions, state):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    events = finalize_events(events, interactions)

    users.to_csv(DATA_DIR / "users.csv", index=False)
    events.to_csv(DATA_DIR / "events.csv", index=False)
    interactions.to_csv(DATA_DIR / "interactions.csv", index=False)

    follows = pd.DataFrame(state.follow_rows, columns=["follower_id", "following_id", "time_created"])
    follows.to_csv(DATA_DIR / "follows.csv", index=False)
    likes = pd.DataFrame(state.like_rows, columns=["liker_id", "liked_id", "event_id", "time_created"])
    likes.to_csv(DATA_DIR / "likes.csv", index=False)
```
Update the imports at the top of `ml/gen/io.py` to:
```python
from ml.gen.splits import finalize_events
```

In `ml/gen/timeline.py`, `main` already calls `write_all` only — no change needed if it does not reference the removed functions. Verify it does not import `build_splits`/`ensure_min_joins`.

- [ ] **Step 6: Update `ml/tests/test_splits.py`**

Replace the entire file with only the finalize-events test (the LOO tests are obsolete):
```python
import numpy as np
from ml.gen.timeline import run_timeline
from ml.gen.splits import finalize_events


def test_finalize_events_emergent_fields(small):
    rng = np.random.default_rng(3)
    users, events, interactions, state = run_timeline(rng)
    events2 = finalize_events(events, interactions)
    for col in ["participant_count", "fill_rate", "social_density_cat", "avg_organizer_rating"]:
        assert col in events2.columns
    assert (events2["participant_count"] >= 0).all()
```

- [ ] **Step 7: Run the full suite**

Run: `python -m pytest -q`
Expected: all pass (the io smoke test still passes because `write_all` writes the core files; if `test_io_smoke.py` asserts the presence of `train.csv`/`test.csv`/`cold_start_users.csv`, update those assertions to check only `users.csv`, `events.csv`, `interactions.csv`, `follows.csv`, `likes.csv`).

- [ ] **Step 8: Commit**

```bash
git add ml/gen/users.py ml/gen/splits.py ml/gen/io.py ml/gen/timeline.py ml/tests/test_splits.py ml/tests/test_cold_flag.py ml/tests/test_io_smoke.py
git commit -m "feat(gen): add is_cold_user flag; drop LOO split outputs (temporal split moves to eval)"
```

---

## Task 4: Candidate construction

**Files:**
- Create: `ml/eval/candidates.py`
- Test: `ml/tests/test_candidates.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_candidates.py`:
```python
import numpy as np
import pandas as pd
from ml.eval.candidates import relevant_set, feasible_candidates


def _events():
    return pd.DataFrame({
        "event_id": [0, 1, 2, 3],
        "activity_id": [1, 1, 2, 1],
        "sport_cluster": [1, 1, 2, 1],
        "max_participants": [10, 10, 10, 10],
        "participant_count": [2, 2, 2, 10],          # event 3 is full
        "day_of_week": [0, 1, 0, 0],
        "time_of_day": [0, 0, 0, 0],
        "latitude": [45.81, 45.81, 45.81, 45.81],
        "longitude": [15.97, 15.97, 15.97, 15.97],
        "start_time": pd.to_datetime(["2023-06-01", "2023-06-02", "2023-06-03", "2023-06-04"]),
        "end_time":   pd.to_datetime(["2023-06-01 02:00", "2023-06-02 02:00", "2023-06-03 02:00", "2023-06-04 02:00"]),
    })


def _user():
    return pd.Series({
        "user_id": 0, "latitude": 45.81, "longitude": 15.97,
        "max_travel_distance": 50, "availability_days": "0,1",
        "availability_times": "0",
    })


def test_relevant_set_uses_test_positives():
    test_df = pd.DataFrame({
        "user_id": [0, 0, 0],
        "event_id": [0, 3, 2],
        "signal_type": ["join_rated", "leave", "join_no_rate"],
        "rating": [4, None, None],
    })
    rel = relevant_set(0, test_df)              # event 0 (rated 4) and event 2 (no_rate, floor)
    assert rel == {0: 4, 2: 1}                  # leave (event 3) excluded


def test_feasible_filters_full_and_unavailable():
    cand = feasible_candidates(_user(), _events(), already_seen=set())
    # event 3 is full -> excluded; event 2 is on an available day/time but different activity is allowed
    assert 3 not in cand
    assert 0 in cand and 1 in cand
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_candidates.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write the implementation**

`ml/eval/candidates.py`:
```python
"""Per-user relevant set and feasible full-catalog candidate set for the test window."""
import numpy as np
import pandas as pd


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def relevant_set(user_id: int, test_df: pd.DataFrame) -> dict:
    """event_id -> graded relevance for a user's positive test-window interactions.

    join_rated -> rating; join_no_rate -> 1 (floor); leave -> excluded.
    """
    rows = test_df[test_df["user_id"] == user_id]
    rel = {}
    for r in rows.itertuples(index=False):
        if r.signal_type == "leave":
            continue
        if r.signal_type == "join_rated":
            rel[int(r.event_id)] = int(r.rating)
        else:  # join_no_rate
            rel[int(r.event_id)] = 1
    return rel


def feasible_candidates(user: pd.Series, events: pd.DataFrame,
                        already_seen: set) -> np.ndarray:
    """All events that pass the hard feasibility filter for this user."""
    days = set(int(x) for x in str(user["availability_days"]).split(","))
    times = set(int(x) for x in str(user["availability_times"]).split(","))
    max_km = max(float(user["max_travel_distance"]), 1.0)

    dist = _haversine_km(float(user["latitude"]), float(user["longitude"]),
                         events["latitude"].values, events["longitude"].values)
    ok = (
        events["day_of_week"].isin(days).values
        & events["time_of_day"].isin(times).values
        & (dist <= max_km)
        & (events["participant_count"].values < events["max_participants"].values)
        & (~events["event_id"].isin(already_seen).values)
    )
    return events.loc[ok, "event_id"].values.astype(int)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_candidates.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/eval/candidates.py ml/tests/test_candidates.py
git commit -m "feat(eval): relevant set + feasible full-catalog candidates"
```

---

## Task 5: Slices

**Files:**
- Create: `ml/eval/slices.py`
- Test: `ml/tests/test_slices.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_slices.py`:
```python
import pandas as pd
from ml.eval.slices import classify_users, new_event_ids


def test_classify_users_warm_cold():
    users = pd.DataFrame({"user_id": [0, 1, 2], "is_cold_user": [False, False, True]})
    train = pd.DataFrame({"user_id": [0], "event_id": [5]})   # only user 0 has train history
    cls = classify_users(users, train)
    assert cls[0] == "warm"
    assert cls[2] == "cold"
    assert cls[1] == "warm_no_history"   # non-cold but no train rows


def test_new_event_ids():
    train = pd.DataFrame({"event_id": [0, 1]})
    test = pd.DataFrame({"event_id": [1, 2, 3]})
    assert new_event_ids(train, test) == {2, 3}     # events not seen in train
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_slices.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write the implementation**

`ml/eval/slices.py`:
```python
"""Slice classification for evaluation reporting."""
import pandas as pd


def classify_users(users: pd.DataFrame, train: pd.DataFrame) -> dict:
    """user_id -> 'cold' | 'warm' | 'warm_no_history'."""
    cold = set(users.loc[users["is_cold_user"], "user_id"].astype(int))
    has_train = set(train["user_id"].astype(int))
    out = {}
    for uid in users["user_id"].astype(int):
        if uid in cold:
            out[uid] = "cold"
        elif uid in has_train:
            out[uid] = "warm"
        else:
            out[uid] = "warm_no_history"
    return out


def new_event_ids(train: pd.DataFrame, test: pd.DataFrame) -> set:
    """Events that appear in test but never in train (no prior attendance history)."""
    seen = set(train["event_id"].astype(int))
    return set(test["event_id"].astype(int)) - seen
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_slices.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/eval/slices.py ml/tests/test_slices.py
git commit -m "feat(eval): warm/cold/new-event slice classification"
```

---

## Task 6: Harness

**Files:**
- Create: `ml/eval/harness.py`
- Test: `ml/tests/test_harness.py`

- [ ] **Step 1: Write the failing test**

`ml/tests/test_harness.py`:
```python
import numpy as np
import pandas as pd
from ml.eval.harness import evaluate, EvalData


class OracleModel:
    """Scores known relevant events highest — should achieve NDCG@10 ~ 1.0."""
    name = "oracle"
    def __init__(self, rel_lookup): self.rel = rel_lookup
    def fit(self, ctx): pass
    def score(self, user_id, cand_ids):
        return np.array([self.rel.get(user_id, {}).get(int(e), 0) for e in cand_ids], float)


def _toy_eval_data():
    users = pd.DataFrame({
        "user_id": [0, 1], "is_cold_user": [False, True],
        "latitude": [45.81, 45.81], "longitude": [15.97, 15.97],
        "max_travel_distance": [50, 50],
        "availability_days": ["0,1,2", "0,1,2"], "availability_times": ["0", "0"],
    })
    events = pd.DataFrame({
        "event_id": [0, 1, 2, 3], "activity_id": [1, 1, 1, 1], "sport_cluster": [1, 1, 1, 1],
        "max_participants": [10, 10, 10, 10], "participant_count": [1, 1, 1, 1],
        "day_of_week": [0, 1, 2, 0], "time_of_day": [0, 0, 0, 0],
        "latitude": [45.81] * 4, "longitude": [15.97] * 4,
        "start_time": pd.to_datetime(["2023-09-01", "2023-09-02", "2023-09-03", "2023-09-04"]),
        "end_time": pd.to_datetime(["2023-09-01 02:00", "2023-09-02 02:00", "2023-09-03 02:00", "2023-09-04 02:00"]),
    })
    train = pd.DataFrame({"user_id": [0], "event_id": [9]})   # user 0 warm
    test = pd.DataFrame({
        "user_id": [0, 1], "event_id": [2, 3],
        "signal_type": ["join_rated", "join_rated"], "rating": [4, 4],
    })
    return EvalData(users=users, events=events, train=train, val=train.iloc[0:0], test=test)


def test_oracle_scores_well_overall_and_slices():
    data = _toy_eval_data()
    rel = {0: {2: 4}, 1: {3: 4}}
    res = evaluate(OracleModel(rel), data)
    assert res["overall"]["ndcg@10"] > 0.99
    assert res["cold"]["ndcg@10"] > 0.99       # user 1 is cold
    assert res["warm"]["ndcg@10"] > 0.99       # user 0 is warm
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest ml/tests/test_harness.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Write the implementation**

`ml/eval/harness.py`:
```python
"""Run a recommender through the temporal full-catalog protocol and report metrics."""
from typing import NamedTuple

import numpy as np
import pandas as pd

from ml.eval.metrics import ndcg_at_k, recall_at_k
from ml.eval.candidates import relevant_set, feasible_candidates
from ml.eval.slices import classify_users, new_event_ids


class EvalData(NamedTuple):
    users: pd.DataFrame
    events: pd.DataFrame
    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame


def _mean(d):
    return float(np.mean(d)) if d else 0.0


def evaluate(model, data: EvalData, k: int = 10) -> dict:
    users = data.users.set_index("user_id", drop=False)
    cls = classify_users(data.users, data.train)
    new_events = new_event_ids(data.train, data.test)
    seen_before = (data.train.groupby("user_id")["event_id"]
                   .agg(lambda s: set(int(x) for x in s)).to_dict())

    buckets = {s: {"ndcg": [], "recall": []} for s in
               ["overall", "warm", "cold", "new_event"]}

    test_users = data.test["user_id"].unique()
    for uid in test_users:
        uid = int(uid)
        rel = relevant_set(uid, data.test)
        if not rel:
            continue
        cand = feasible_candidates(users.loc[uid], data.events,
                                   already_seen=seen_before.get(uid, set()))
        cand = np.union1d(cand, np.array(list(rel.keys()), dtype=int))
        scores = np.asarray(model.score(uid, cand), dtype=float)
        rels = np.array([rel.get(int(e), 0) for e in cand], dtype=float)

        nd = ndcg_at_k(scores, rels, k)
        rc = recall_at_k(scores, rels, k)
        buckets["overall"]["ndcg"].append(nd); buckets["overall"]["recall"].append(rc)
        slice_name = "cold" if cls.get(uid) == "cold" else "warm"
        if slice_name in ("warm", "cold"):
            buckets[slice_name]["ndcg"].append(nd); buckets[slice_name]["recall"].append(rc)

        # new-event slice: restrict relevance to events new in the test window
        if any(e in new_events for e in rel):
            ne_rels = np.array([(rel.get(int(e), 0) if int(e) in new_events else 0)
                                for e in cand], dtype=float)
            buckets["new_event"]["ndcg"].append(ndcg_at_k(scores, ne_rels, k))
            buckets["new_event"]["recall"].append(recall_at_k(scores, ne_rels, k))

    return {s: {"ndcg@10": _mean(b["ndcg"]), "recall@10": _mean(b["recall"]),
                "n": len(b["ndcg"])}
            for s, b in buckets.items()}
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest ml/tests/test_harness.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add ml/eval/harness.py ml/tests/test_harness.py
git commit -m "feat(eval): full-catalog temporal harness with sliced NDCG@10/Recall@10"
```

---

## Self-review notes (spec coverage)

- Temporal split + strict ordering + cold exclusion → Task 2.
- Full-catalog feasible candidates (no sampling) → Task 4.
- Weighted NDCG@10 + Recall@10, explicit formulas → Task 1.
- Slices overall/warm/cold/new-event → Tasks 5, 6.
- Harness + model interface (`fit`/`score`) → Task 6.
- Generator: drop LOO, add `is_cold_user` → Task 3.
- `features.py` temporal consumption: handled in the model-suite plan (models build `TrainContext` from `train`), since features are only needed by the models, not by the harness itself.

**Known follow-ups:** default boundaries `t1q=0.70, t2q=0.85` may be tuned so the test
window contains enough events/users per slice; verify slice `n` counts after the
first real run.
