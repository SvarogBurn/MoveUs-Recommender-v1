import numpy as np
import pandas as pd
from ml.models.random_rec import RandomRec
from ml.models.popularity import PopularityRec
from ml.models.base import TrainContext
from ml.models.context import build_feature_context


def _ctx():
    users = pd.DataFrame({"user_id": [0], "is_cold_user": [False],
                          "latitude": [45.8], "longitude": [15.9], "max_travel_distance": [50],
                          "availability_days": ["0,1,2,3,4,5,6"], "availability_times": ["0,1,2,3"],
                          "preferred_activities": ["1"], "preferred_skills": ["2"],
                          "preferred_group_size": [5], "preferred_session_duration": [90],
                          "motivated_by_competition": [3]})
    events = pd.DataFrame({"event_id": [10, 11], "activity_id": [1, 1], "sport_cluster": [1, 1],
                           "skill_level": [2, 2], "max_participants": [10, 10], "participant_count": [3, 9],
                           "duration_hours": [1.5, 1.5], "day_of_week": [0, 0], "time_of_day": [0, 0],
                           "latitude": [45.8, 45.8], "longitude": [15.9, 15.9],
                           "start_time": pd.to_datetime(["2023-03-01", "2023-03-02"]),
                           "end_time": pd.to_datetime(["2023-03-01 02:00", "2023-03-02 02:00"])})
    train = pd.DataFrame({"user_id": [0, 0, 0], "event_id": [10, 10, 11],
                          "signal_type": ["join_rated"] * 3, "rating": [4, 4, 3],
                          "activity_id": [1, 1, 1], "sport_cluster": [1, 1, 1],
                          "timestamp": pd.to_datetime(["2023-02-01", "2023-02-02", "2023-02-03"])})
    fc = build_feature_context(train, users, events)
    return TrainContext(users=users, events=events, train=train, features=fc)


def test_random_returns_finite_array():
    ctx = _ctx(); m = RandomRec(seed=0); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))
    assert s.shape == (2,) and np.isfinite(s).all()


def test_popularity_prefers_more_attended_event():
    ctx = _ctx(); m = PopularityRec(); m.fit(ctx)
    s = m.score(0, np.array([10, 11]))           # event 10 attended twice, 11 once
    assert s[0] > s[1]
