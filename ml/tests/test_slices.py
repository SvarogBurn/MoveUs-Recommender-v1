import pandas as pd
from ml.eval.slices import classify_users, new_event_ids


def test_classify_users_warm_cold():
    users = pd.DataFrame({"user_id": [0, 1, 2], "is_cold_user": [False, False, True]})
    train = pd.DataFrame({"user_id": [0], "event_id": [5]})   # only user 0 has train history
    cls = classify_users(users, train)
    assert cls[0] == "warm"
    assert cls[2] == "cold"
    assert cls[1] == "warm_no_history"   # non-cold but no train rows


def test_new_event_ids():
    train = pd.DataFrame({"event_id": [0, 1]})
    test = pd.DataFrame({"event_id": [1, 2, 3]})
    assert new_event_ids(train, test) == {2, 3}     # events not seen in train
