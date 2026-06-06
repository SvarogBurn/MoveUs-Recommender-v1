import numpy as np
import pandas as pd
from ml.eval.harness import evaluate, EvalData


class OracleModel:
    """Scores known relevant events highest — should achieve NDCG@10 ~ 1.0."""
    name = "oracle"
    def __init__(self, rel_lookup): self.rel = rel_lookup
    def fit(self, ctx): pass
    def score(self, user_id, cand_ids):
        return np.array([self.rel.get(user_id, {}).get(int(e), 0) for e in cand_ids], float)


def _toy_eval_data():
    users = pd.DataFrame({
        "user_id": [0, 1], "is_cold_user": [False, True],
        "latitude": [45.81, 45.81], "longitude": [15.97, 15.97],
        "max_travel_distance": [50, 50],
        "availability_days": ["0,1,2", "0,1,2"], "availability_times": ["0", "0"],
    })
    events = pd.DataFrame({
        "event_id": [0, 1, 2, 3], "activity_id": [1, 1, 1, 1], "sport_cluster": [1, 1, 1, 1],
        "max_participants": [10, 10, 10, 10], "participant_count": [1, 1, 1, 1],
        "day_of_week": [0, 1, 2, 0], "time_of_day": [0, 0, 0, 0],
        "latitude": [45.81] * 4, "longitude": [15.97] * 4,
        "start_time": pd.to_datetime(["2023-09-01", "2023-09-02", "2023-09-03", "2023-09-04"]),
        "end_time": pd.to_datetime(["2023-09-01 02:00", "2023-09-02 02:00", "2023-09-03 02:00", "2023-09-04 02:00"]),
    })
    train = pd.DataFrame({"user_id": [0], "event_id": [9]})   # user 0 warm
    test = pd.DataFrame({
        "user_id": [0, 1], "event_id": [2, 3],
        "signal_type": ["join_rated", "join_rated"], "rating": [4, 4],
    })
    return EvalData(users=users, events=events, train=train, val=train.iloc[0:0], test=test)


def test_oracle_scores_well_overall_and_slices():
    data = _toy_eval_data()
    rel = {0: {2: 4}, 1: {3: 4}}
    res = evaluate(OracleModel(rel), data)
    assert res["overall"]["ndcg@10"] > 0.99
    assert res["cold"]["ndcg@10"] > 0.99       # user 1 is cold
    assert res["warm"]["ndcg@10"] > 0.99       # user 0 is warm
