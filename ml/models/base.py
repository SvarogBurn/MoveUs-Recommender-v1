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
    follows: object = None       # DataFrame[follower_id, following_id]; optional social graph
