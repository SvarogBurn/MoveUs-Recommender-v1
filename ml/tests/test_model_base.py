import numpy as np
from ml.models.base import Recommender, TrainContext


def test_recommender_protocol_runtime_checkable():
    class Dummy:
        name = "dummy"
        def fit(self, ctx): pass
        def score(self, uid, cand): return np.zeros(len(cand))
    assert isinstance(Dummy(), Recommender)


def test_traincontext_holds_frames():
    import pandas as pd
    ctx = TrainContext(users=pd.DataFrame({"user_id": [0]}),
                       events=pd.DataFrame({"event_id": [0]}),
                       train=pd.DataFrame({"user_id": [0], "event_id": [0]}),
                       features=None)
    assert ctx.users.iloc[0]["user_id"] == 0
