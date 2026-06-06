import numpy as np
from ml.models.bpr_mf import BPRMFRec
from ml.tests.test_baselines import _ctx


def test_bpr_scores_and_falls_back_for_unseen():
    ctx = _ctx()
    m = BPRMFRec(epochs=3, seed=0); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))           # user 0 + events 10/11 are in train
    assert s.shape == (2,) and np.isfinite(s).all()
    s_cold = m.score(999, np.array([10, 11]))     # unseen user -> fallback, still finite
    assert np.isfinite(s_cold).all()
