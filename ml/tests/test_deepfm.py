import numpy as np
from ml.models.deepfm import DeepFMRec
from ml.tests.test_baselines import _ctx


def test_deepfm_fits_and_scores():
    ctx = _ctx()
    m = DeepFMRec(epochs=2, seed=0); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))
    assert s.shape == (2,) and np.isfinite(s).all()
