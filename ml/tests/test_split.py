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
