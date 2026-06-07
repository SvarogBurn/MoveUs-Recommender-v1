import numpy as np
import pandas as pd

from ml.models.base import TrainContext
from ml.models.context import build_feature_context
from ml.models._torch_pairs import build_pos_neg_rows


def _ctx_with_infeasible():
    users = pd.DataFrame({
        "user_id": [0], "is_cold_user": [False],
        "latitude": [45.8], "longitude": [15.9], "max_travel_distance": [50],
        "availability_days": ["0"], "availability_times": ["0"],
        "preferred_activities": ["1"], "preferred_skills": ["2"],
        "preferred_group_size": [5], "preferred_session_duration": [90],
        "motivated_by_competition": [3],
    })
    events = pd.DataFrame({
        "event_id": [10, 11, 12], "activity_id": [1, 1, 1], "sport_cluster": [1, 1, 1],
        "skill_level": [2, 2, 2], "max_participants": [10, 10, 10], "participant_count": [3, 3, 3],
        "duration_hours": [1.5, 1.5, 1.5],
        "day_of_week": [0, 5, 0],                      # event 11 is on an unavailable day
        "time_of_day": [0, 0, 0],
        "latitude": [45.8, 45.8, 45.8], "longitude": [15.9, 15.9, 15.9],
        "start_time": pd.to_datetime(["2023-03-01", "2023-03-02", "2023-03-03"]),
        "end_time": pd.to_datetime(["2023-03-01 02:00", "2023-03-02 02:00", "2023-03-03 02:00"]),
    })
    train = pd.DataFrame({
        "user_id": [0], "event_id": [10], "signal_type": ["join_rated"], "rating": [4],
        "activity_id": [1], "sport_cluster": [1], "timestamp": pd.to_datetime(["2023-02-01"]),
    })
    fc = build_feature_context(train, users, events)
    return TrainContext(users=users, events=events, train=train, features=fc)


def test_negatives_are_feasible_and_unattended():
    ctx = _ctx_with_infeasible()
    pos_rows, neg_rows = build_pos_neg_rows(ctx, neg_per_pos=4, seed=0)
    assert pos_rows == [(0, 10)]
    neg_events = {e for _, e in neg_rows}
    # only event 12 is feasible (day 0) and not yet attended; 11 is infeasible, 10 attended
    assert neg_events == {12}
