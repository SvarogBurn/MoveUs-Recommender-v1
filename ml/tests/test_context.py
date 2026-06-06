import numpy as np
import pandas as pd
from ml.models.context import build_feature_context


def _toy():
    users = pd.DataFrame({
        "user_id": [0, 1], "is_cold_user": [False, True],
        "latitude": [45.81, 45.81], "longitude": [15.97, 15.97],
        "max_travel_distance": [50, 50],
        "availability_days": ["0,1,2,3,4,5,6", "0,1,2,3,4,5,6"],
        "availability_times": ["0,1,2,3", "0,1,2,3"],
        "preferred_activities": ["1", "1"], "preferred_skills": ["2", "2"],
        "preferred_group_size": [5, 5], "preferred_session_duration": [90, 90],
        "motivated_by_competition": [3, 3],
    })
    events = pd.DataFrame({
        "event_id": [10, 11], "activity_id": [1, 2], "sport_cluster": [1, 2],
        "skill_level": [2, 2], "max_participants": [10, 10], "participant_count": [3, 3],
        "duration_hours": [1.5, 1.5], "day_of_week": [0, 0], "time_of_day": [0, 0],
        "latitude": [45.81, 45.81], "longitude": [45.81, 45.81],
        "start_time": pd.to_datetime(["2023-03-01", "2023-03-02"]),
        "end_time": pd.to_datetime(["2023-03-01 02:00", "2023-03-02 02:00"]),
    })
    train = pd.DataFrame({
        "user_id": [0], "event_id": [10], "signal_type": ["join_rated"],
        "rating": [4], "activity_id": [1], "sport_cluster": [1],
        "timestamp": pd.to_datetime(["2023-02-01"]),
    })
    return users, events, train


def test_pair_dense_shape_and_finiteness():
    users, events, train = _toy()
    fc = build_feature_context(train, users, events)
    X = fc.pair_dense(0, np.array([10, 11]))
    assert X.shape[0] == 2
    assert np.isfinite(X).all()


def test_user_event_id_maps():
    users, events, train = _toy()
    fc = build_feature_context(train, users, events)
    assert fc.has_user(0) and not fc.has_user(1)        # user 1 has no train rows
    assert fc.has_event(10) and not fc.has_event(11)
