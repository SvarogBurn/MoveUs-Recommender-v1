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
