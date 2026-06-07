"""Time-windowed, per-target evaluation protocol (step 1 of the protocol fix)."""
import numpy as np
import pandas as pd

from ml.eval.harness import evaluate, EvalData


def _events():
    # five events; #10 is a far-future distractor that no ±7d window should ever reach
    return pd.DataFrame({
        "event_id":         [0, 1, 2, 3, 10],
        "activity_id":      [1, 1, 1, 1, 1],
        "sport_cluster":    [1, 1, 1, 1, 1],
        "max_participants": [10, 10, 10, 10, 10],
        "participant_count":[1, 1, 1, 1, 1],
        "day_of_week":      [0, 0, 0, 0, 0],
        "time_of_day":      [0, 0, 0, 0, 0],
        "latitude":         [45.81] * 5,
        "longitude":        [15.97] * 5,
        "start_time": pd.to_datetime(
            ["2023-09-10", "2023-09-11", "2023-09-12", "2023-09-13", "2024-01-01"]),
        "end_time": pd.to_datetime(
            ["2023-09-10 02:00", "2023-09-11 02:00", "2023-09-12 02:00",
             "2023-09-13 02:00", "2024-01-01 02:00"]),
    })


def _users():
    return pd.DataFrame({
        "user_id": [0, 1], "is_cold_user": [False, True],
        "latitude": [45.81, 45.81], "longitude": [15.97, 15.97],
        "max_travel_distance": [50, 50],
        "availability_days": ["0", "0"], "availability_times": ["0", "0"],
    })


def _data():
    # user 0 (warm): two positives inside one window; user 1 (cold): one positive
    train = pd.DataFrame({"user_id": [0], "event_id": [99]})
    test = pd.DataFrame({
        "user_id":     [0, 0, 1],
        "event_id":    [1, 2, 3],
        "signal_type": ["join_rated", "join_rated", "join_rated"],
        "rating":      [4, 2, 4],
    })
    return EvalData(users=_users(), events=_events(),
                    train=train, val=train.iloc[0:0], test=test)


class _Recorder:
    name = "recorder"
    def __init__(self): self.seen = []
    def fit(self, ctx): pass
    def score(self, user_id, cand_ids):
        self.seen.append(set(int(e) for e in cand_ids))
        return np.zeros(len(cand_ids))


class _ScoreEvent:
    """Scores one chosen event highest, everything else 0."""
    name = "score_event"
    def __init__(self, eid): self.eid = eid
    def fit(self, ctx): pass
    def score(self, user_id, cand_ids):
        return np.array([1.0 if int(e) == self.eid else 0.0 for e in cand_ids], float)


def test_out_of_window_events_never_enter_any_candidate_pool():
    rec = _Recorder()
    evaluate(rec, _data())
    assert rec.seen, "model was never scored"
    for pool in rec.seen:
        assert 10 not in pool                 # far-future distractor excluded everywhere
        assert pool <= {0, 1, 2, 3}


def test_instances_are_per_target():
    rec = _Recorder()
    res = evaluate(rec, _data())
    assert res["overall"]["n"] == 3           # one instance per test positive row


def test_pool_size_is_reported():
    res = evaluate(_Recorder(), _data())
    assert res["overall"]["pool_size"] == 4   # {0,1,2,3} in every ±7d window


def test_new_event_slice_is_dropped():
    res = evaluate(_Recorder(), _data())
    assert "new_event" not in res
    assert set(res) >= {"overall", "warm", "cold"}


def test_co_window_positives_are_graded_relevant():
    # user 0 attended events 1 and 2 in the same window. Scoring only event 1
    # highest must yield recall@1 = 0.5 for that instance (denominator = 2),
    # which proves event 2 is counted as relevant rather than as a negative.
    res = evaluate(_ScoreEvent(1), _data(), k=1)
    assert res["warm"]["recall@10"] == 0.5


def _data_split_windows():
    # user 0 has two positives far apart in time -> two separate instances/windows
    train = pd.DataFrame({"user_id": [0], "event_id": [99]})
    events = _events().copy()
    events.loc[events["event_id"] == 10, "event_id"] = 20   # rename far event to 20
    test = pd.DataFrame({
        "user_id":     [0, 0],
        "event_id":    [1, 20],
        "signal_type": ["join_rated", "join_rated"],
        "rating":      [4, 4],
    })
    return EvalData(users=_users(), events=events,
                    train=train, val=train.iloc[0:0], test=test)


def test_out_of_window_positive_is_not_relevant_for_an_instance():
    # Each instance only counts positives inside its own ±7d window as relevant.
    # Scoring event 1 highest is perfect for the Sept window; the far-future
    # instance (event 20, alone in its window) is also satisfied -> recall 1.0.
    # Under per-user pooling, event 20 would dilute the Sept instance (recall 0.5).
    res = evaluate(_ScoreEvent(1), _data_split_windows(), k=1)
    assert res["warm"]["recall@10"] == 1.0
