"""Run a recommender through the temporal full-catalog protocol and report metrics."""
from typing import NamedTuple

import numpy as np
import pandas as pd

from ml.eval.metrics import ndcg_at_k, recall_at_k, reciprocal_rank
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

    buckets = {s: {"ndcg": [], "recall": [], "mrr": []} for s in
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
        rr = reciprocal_rank(scores, rels)
        buckets["overall"]["ndcg"].append(nd); buckets["overall"]["recall"].append(rc)
        buckets["overall"]["mrr"].append(rr)
        slice_name = "cold" if cls.get(uid) == "cold" else "warm"
        if slice_name in ("warm", "cold"):
            buckets[slice_name]["ndcg"].append(nd); buckets[slice_name]["recall"].append(rc)
            buckets[slice_name]["mrr"].append(rr)

        # new-event slice: restrict relevance to events new in the test window
        if any(e in new_events for e in rel):
            ne_rels = np.array([(rel.get(int(e), 0) if int(e) in new_events else 0)
                                for e in cand], dtype=float)
            buckets["new_event"]["ndcg"].append(ndcg_at_k(scores, ne_rels, k))
            buckets["new_event"]["recall"].append(recall_at_k(scores, ne_rels, k))
            buckets["new_event"]["mrr"].append(reciprocal_rank(scores, ne_rels))

    return {s: {"ndcg@10": _mean(b["ndcg"]), "recall@10": _mean(b["recall"]),
                "mrr": _mean(b["mrr"]), "n": len(b["ndcg"])}
            for s, b in buckets.items()}
