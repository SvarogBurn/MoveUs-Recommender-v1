import numpy as np
from ml.models.logreg import LogRegRec
from ml.tests.test_baselines import _ctx     # reuse the toy context


def test_logreg_fits_and_scores():
    ctx = _ctx()
    m = LogRegRec(); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))
    assert s.shape == (2,) and np.isfinite(s).all()
    assert ((s >= 0) & (s <= 1)).all()         # probabilities
