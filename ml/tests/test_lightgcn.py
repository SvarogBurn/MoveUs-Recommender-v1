import numpy as np
from ml.models.lightgcn import LightGCNRec
from ml.tests.test_baselines import _ctx


def test_lightgcn_scores_and_falls_back():
    ctx = _ctx()
    m = LightGCNRec(epochs=3, layers=2, seed=0); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))
    assert s.shape == (2,) and np.isfinite(s).all()
    assert np.isfinite(m.score(999, np.array([10]))).all()   # unseen -> fallback
