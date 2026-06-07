"""Step 3: collaborative models key items on activity (a recurring node), so they
can score brand-new events that never appeared in training."""
import numpy as np
import pandas as pd

from ml.models.base import TrainContext
from ml.models.context import build_feature_context
from ml.models.popularity import PopularityRec
from ml.models.bpr_mf import BPRMFRec
from ml.models.lightgcn import LightGCNRec


def _ctx_new_event():
    users = pd.DataFrame({
        "user_id": [0], "is_cold_user": [False],
        "latitude": [45.8], "longitude": [15.9], "max_travel_distance": [50],
        "availability_days": ["0,1,2,3,4,5,6"], "availability_times": ["0,1,2,3"],
        "preferred_activities": ["1"], "preferred_skills": ["2"],
        "preferred_group_size": [5], "preferred_session_duration": [90],
        "motivated_by_competition": [3],
    })
    # events 12 & 13 are brand-new (not in train) and BOTH map to cluster 1, so a
    # cluster-match baseline cannot tell them apart. Only their activity differs:
    # activity 1 is attended in train, activity 9 never is. (ACTIVITY_CLUSTER[1]=
    # ACTIVITY_CLUSTER[9]=1.) Event 11 (activity 2) is a never-attended distractor.
    events = pd.DataFrame({
        "event_id": [10, 11, 12, 13], "activity_id": [1, 2, 1, 9], "sport_cluster": [1, 0, 1, 1],
        "skill_level": [2, 2, 2, 2], "max_participants": [10, 10, 10, 10],
        "participant_count": [3, 3, 3, 3], "duration_hours": [1.5, 1.5, 1.5, 1.5],
        "day_of_week": [0, 0, 0, 0], "time_of_day": [0, 0, 0, 0],
        "latitude": [45.8] * 4, "longitude": [15.9] * 4,
        "start_time": pd.to_datetime(["2023-03-01", "2023-03-02", "2023-03-03", "2023-03-03"]),
        "end_time": pd.to_datetime(["2023-03-01 02:00", "2023-03-02 02:00",
                                    "2023-03-03 02:00", "2023-03-03 02:00"]),
    })
    train = pd.DataFrame({
        "user_id": [0], "event_id": [10], "signal_type": ["join_rated"], "rating": [4],
        "activity_id": [1], "sport_cluster": [1], "timestamp": pd.to_datetime(["2023-02-01"]),
    })
    fc = build_feature_context(train, users, events)
    return TrainContext(users=users, events=events, train=train, features=fc)


def test_popularity_scores_new_event_by_activity_popularity():
    m = PopularityRec(); m.fit(_ctx_new_event())
    # both new and in the same cluster; only activity popularity separates them
    s = m.score(0, np.array([12, 13]))
    assert s[0] > s[1]


def test_bpr_scores_new_event_via_activity_embedding():
    ctx = _ctx_new_event()
    m = BPRMFRec(epochs=3, seed=0); m.fit(ctx)
    assert m.event_activity[12] in m.act_index      # new event maps to a trained activity node
    assert np.isfinite(m.score(0, np.array([12]))).all()


def test_lightgcn_scores_new_event_via_activity_embedding():
    ctx = _ctx_new_event()
    m = LightGCNRec(epochs=3, layers=2, seed=0); m.fit(ctx)
    assert m.event_activity[12] in m.act_index
    assert np.isfinite(m.score(0, np.array([12]))).all()
