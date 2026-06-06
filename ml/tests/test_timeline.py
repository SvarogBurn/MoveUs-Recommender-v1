import numpy as np
import pandas as pd
from ml.gen.timeline import run_timeline


def test_run_timeline_produces_interactions(small):
    rng = np.random.default_rng(7)
    users, events, interactions, state = run_timeline(rng)
    assert len(interactions) > 0
    # chronological
    ts = pd.to_datetime(interactions["timestamp"]).values
    assert (ts[:-1] <= ts[1:]).all()
    # no user in two overlapping events: check each user's booked intervals are disjoint
    for u, ivs in state._booked.items():
        ivs = sorted(ivs)
        for a, b in zip(ivs, ivs[1:]):
            assert a[1] <= b[0]


def test_no_legacy_columns(small):
    rng = np.random.default_rng(7)
    _, _, interactions, _ = run_timeline(rng)
    assert "organizer_is_followed" not in interactions.columns
