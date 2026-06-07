"""Run a recommender through the temporal full-catalog protocol and report metrics."""
from typing import NamedTuple

import numpy as np
import pandas as pd

from ml.eval.metrics import ndcg_at_k, recall_at_k, reciprocal_rank
from ml.eval.candidates import feasible_candidates
from ml.eval.slices import classify_users


class EvalData(NamedTuple):
    users: pd.DataFrame
    events: pd.DataFrame
    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame


def _mean(d):
    return float(np.mean(d)) if d else 0.0


def _user_positives(test: pd.DataFrame) -> dict:
    """user_id -> {event_id: graded relevance} over positive test interactions.

    join_rated -> rating (rating 0 is non-relevant and dropped); join_no_rate -> 1;
    leave -> excluded.
    """
    pos = {}
    for r in test.itertuples(index=False):
        if r.signal_type == "leave":
            continue
        grade = int(r.rating) if r.signal_type == "join_rated" else 1
        if grade <= 0:
            continue
        pos.setdefault(int(r.user_id), {})[int(r.event_id)] = grade
    return pos


def evaluate(model, data: EvalData, k: int = 10, horizon_days: int = 7) -> dict:
    """Per-target, time-windowed full-catalog evaluation.

    One ranking instance per positive test interaction. The candidate pool is the
    set of feasible events starting within a ``horizon_days`` window centred on the
    target's start time. Any of the user's positives inside that same window count
    as graded-relevant, so NDCG keeps its graded meaning.
    """
    users = data.users.set_index("user_id", drop=False)
    cls = classify_users(data.users, data.train)
    seen_before = (data.train.groupby("user_id")["event_id"]
                   .agg(lambda s: set(int(x) for x in s)).to_dict())
    event_start = data.events.set_index("event_id")["start_time"]
    user_pos = _user_positives(data.test)

    horizon = pd.Timedelta(days=horizon_days)
    half = horizon / 2

    buckets = {s: {"ndcg": [], "recall": [], "mrr": [], "pool": []}
               for s in ["overall", "warm", "cold"]}

    for uid, positives in user_pos.items():
        slice_name = "cold" if cls.get(uid) == "cold" else "warm"
        for target_eid in positives:
            t_start = event_start.loc[target_eid]
            decision_time = t_start - half
            window_end = decision_time + horizon

            cand = feasible_candidates(users.loc[uid], data.events,
                                       already_seen=seen_before.get(uid, set()),
                                       decision_time=decision_time, horizon=horizon)
            # relevant = this user's positives that fall inside the same window
            rel = {e: g for e, g in positives.items()
                   if decision_time <= event_start.loc[e] <= window_end}
            cand = np.union1d(cand, np.array(list(rel.keys()), dtype=int))
            scores = np.asarray(model.score(uid, cand), dtype=float)
            rels = np.array([rel.get(int(e), 0) for e in cand], dtype=float)

            nd = ndcg_at_k(scores, rels, k)
            rc = recall_at_k(scores, rels, k)
            rr = reciprocal_rank(scores, rels)
            for s in ("overall", slice_name):
                buckets[s]["ndcg"].append(nd); buckets[s]["recall"].append(rc)
                buckets[s]["mrr"].append(rr); buckets[s]["pool"].append(len(cand))

    return {s: {"ndcg@10": _mean(b["ndcg"]), "recall@10": _mean(b["recall"]),
                "mrr": _mean(b["mrr"]), "n": len(b["ndcg"]),
                "pool_size": _mean(b["pool"])}
            for s, b in buckets.items()}
