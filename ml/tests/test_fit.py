import numpy as np
from ml.gen import config as c
from ml.gen.fit import personality_fit, dur_fit, size_fit


def test_personality_fit_uses_table17_coefficients():
    # cluster 3 (risk): risk=1.0, social=0.3, consistency=0.3, injury=1.0
    attrs = c.CLUSTER_ATTRS[3]
    O = E = H = N = C_ = 1.0
    expected = (0.42 * O * attrs["risk"] + 0.42 * E * attrs["social"]
                + 0.75 * H * attrs["risk"] - 0.47 * N * attrs["risk"]
                + 0.40 * C_ * attrs["consistency"])
    got = personality_fit(O=O, C=C_, E=E, N=N, H=H, cluster=3)
    assert abs(got - expected) < 1e-9


def test_size_fit_zero_for_fixed_sports():
    # activity 2 = soccer (fixed): size_fit must be 0 regardless of preference
    assert size_fit(pref_size=2, roster_size=20, capacity=22, activity=2) == 0.0
    # activity 0 = hiking (flexible): mismatch penalised (negative)
    assert size_fit(pref_size=2, roster_size=20, capacity=22, activity=0) < 0.0


def test_dur_fit_penalises_mismatch():
    near = dur_fit(pref_minutes=90, event_hours=1.5)   # 90 min == 1.5 h
    far = dur_fit(pref_minutes=30, event_hours=4.0)
    assert near > far
