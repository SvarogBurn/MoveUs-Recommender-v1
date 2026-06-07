import warnings

import numpy as np
from ml.models.lgbm_ranker import LGBMRankerRec
from ml.models.context import FEATURE_NAMES
from ml.tests.test_baselines import _ctx


def test_lgbm_fits_and_scores():
    ctx = _ctx()
    m = LGBMRankerRec(); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))
    assert s.shape == (2,) and np.isfinite(s).all()


def test_lgbm_uses_named_features_and_warns_not():
    # named features on both fit and predict -> sklearn never warns about names
    ctx = _ctx()
    m = LGBMRankerRec(); m.fit(ctx)
    assert list(m.model.feature_names_in_) == FEATURE_NAMES
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        m.score(0, np.array([10, 11]))
