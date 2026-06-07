import numpy as np
from ml.gen.users import generate_users
from ml.gen.events import generate_events
from ml.gen.calibrate import calibrate_propensity


def test_calibration_returns_one_value_per_user(small):
    rng = np.random.default_rng(0)
    users = generate_users(rng)
    events = generate_events(rng, users)
    base = calibrate_propensity(users, events)
    assert base.shape == (len(users),)
    # frequent-tier users should get a higher intercept than sparse-tier on average
    freq = base[users["frequency_tier"].values == "frequent"]
    sparse = base[users["frequency_tier"].values == "sparse"]
    if len(freq) and len(sparse):
        assert np.nanmean(freq) > np.nanmean(sparse)
