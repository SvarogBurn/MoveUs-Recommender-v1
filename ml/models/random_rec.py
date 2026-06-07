"""Uniform random baseline (lower bound)."""
import numpy as np


class RandomRec:
    name = "Random"
    def __init__(self, seed: int = 0):
        self.rng = np.random.default_rng(seed)
    def fit(self, ctx): pass
    def score(self, user_id, candidate_event_ids):
        return self.rng.random(len(candidate_event_ids))
