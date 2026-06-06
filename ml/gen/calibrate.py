"""Per-user base propensity so expected joins ~ tier target."""
import numpy as np

from ml.gen import config as c


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def calibrate_propensity(users, events, delta=0.4):
    """Bisection on a per-user intercept b so sum sigmoid(static + b + delta) ~ target.

    `static` is approximated as a constant activity-match term across the user's
    matchable events; the dynamic social terms are absorbed by `delta`.
    """
    n = len(users)
    base = np.zeros(n)
    n_events = len(events)
    for i in range(n):
        target = c.FREQ_TIER_TARGET[users.iloc[i]["frequency_tier"]]
        lo, hi = -12.0, 6.0
        for _ in range(40):
            mid = (lo + hi) / 2
            expected = n_events * _sigmoid(c.W_ACT * 0.5 + mid + delta)
            if expected > target:
                hi = mid
            else:
                lo = mid
        base[i] = (lo + hi) / 2
    return base
