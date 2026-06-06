import numpy as np
from ml.models.lgbm_ranker import LGBMRankerRec
from ml.tests.test_baselines import _ctx


def test_lgbm_fits_and_scores():
    ctx = _ctx()
    m = LGBMRankerRec(); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))
    assert s.shape == (2,) and np.isfinite(s).all()
