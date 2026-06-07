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
