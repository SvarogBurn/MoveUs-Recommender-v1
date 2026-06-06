"""Sequential enrollment and event resolution."""
from datetime import timedelta

import numpy as np

from ml.gen import config as c
from ml.gen.fit import personality_fit, dur_fit, size_fit, comp_fit


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def _candidate_pool(ev, users, state, rng):
    """Prefilter: matching activity/cluster + within travel + not busy."""
    act = int(ev["activity_id"]); clu = int(ev["sport_cluster"])
    pref_acts = users["preferred_activities"].str.split(",")
    mask = pref_acts.apply(lambda lst: str(act) in lst).values
    # cluster fallback
    for i in np.where(~mask)[0]:
        lst = [int(x) for x in users.iloc[i]["preferred_activities"].split(",")]
        if any(c.ACTIVITY_CLUSTER[a] == clu for a in lst):
            mask[i] = True
    cand = users.index[mask].tolist()
    return [u for u in cand if not state.is_busy(u, ev["start_time"], ev["end_time"])]


def _known_terms(u, roster, users, state, as_of):
    first = second = known = 0
    val = 0.0
    for m in roster:
        if state.follows(u, m, as_of) or state.follows(m, u, as_of):
            first += 1; known += 1
        else:
            v = state.coattend_valence(u, m)
            if v != 0:
                known += 1; val += np.sign(v)
    return {"known": known, "first": first, "valence": val}


def run_enrollment(ev, users, state, base_propensity, rng, max_passes=3):
    cap = int(ev["max_participants"])
    org = int(ev["organizer_id"])
    roster = [org]
    state.book(org, ev["start_time"], ev["end_time"])
    cand = [u for u in _candidate_pool(ev, users, state, rng) if u != org]
    as_of = ev["start_time"]
    clu = int(ev["sport_cluster"]); act = int(ev["activity_id"])
    org_score = state.organizer_score(org)
    org_first = 1 if state.organizer_events(org) == 0 else 0

    for _ in range(max_passes):
        if len(roster) >= cap:
            break
        rng.shuffle(cand)
        progressed = False
        for u in list(cand):
            if len(roster) >= cap:
                break
            urow = users.iloc[u]
            kt = _known_terms(u, roster, users, state, as_of)
            acq_gap = abs(kt["known"] - int(urow["acquaintance_preference"]))
            social = (c.SOCIAL_WEIGHT[urow["motivation_type"]] * kt["valence"]
                      - 0.3 * acq_gap)
            logit = (base_propensity[u]
                     + c.W_ACT * 1.0
                     + c.W_SIZE * size_fit(int(urow["preferred_group_size"]), len(roster), cap, act)
                     + c.W_DUR * dur_fit(int(urow["preferred_session_duration"]), float(ev["duration_hours"]))
                     + c.W_COMP * comp_fit(int(urow["motivated_by_competition"]), int(ev["skill_level"]))
                     + social
                     + c.W_ORG * (org_score / 4.0 - 0.5 * org_first))
            if rng.random() < _sigmoid(logit):
                roster.append(u)
                state.book(u, ev["start_time"], ev["end_time"])
                cand.remove(u)
                progressed = True
        if not progressed:
            break
    return roster


def _valence(rating, left):
    if left:
        return -1.0
    if rating is None:
        return 0.5
    return 1.0 if rating >= 3 else (-1.0 if rating <= 1 else 0.0)


def resolve_event(ev, roster, users, state, rng):
    rows = []
    as_of = ev["start_time"]
    org = int(ev["organizer_id"])
    members = [u for u in roster if u != org]
    motivations = {u: users.iloc[u]["motivation_type"] for u in roster}

    for order, u in enumerate(members):
        urow = users.iloc[u]
        mt = urow["motivation_type"]
        snap = state.history_snapshot(u, int(ev["activity_id"]), int(ev["sport_cluster"]))
        kt = _known_terms(u, roster, users, state, as_of)

        left = rng.random() < c.LEAVE_PROB[mt]
        rated = (not left) and (rng.random() < c.RATE_PROB[mt])

        rating = None
        if rated:
            fit = personality_fit(float(urow["openness"]), float(urow["conscientiousness"]),
                                  float(urow["extraversion"]), float(urow["neuroticism"]),
                                  float(urow["hardiness"]), int(ev["sport_cluster"]))
            base = c.FIT_BASE_SCALE * fit + c.FIT_BASE_OFFSET
            same = sum(1 for v in roster if v != u and motivations[v] == mt)
            homophily = 0.5 if (roster and rng.random() < same / max(len(roster), 1)) else 0.0
            acq_sat = 0.3 if abs(kt["known"] - int(urow["acquaintance_preference"])) <= 1 else 0.0
            raw = base + homophily + acq_sat + rng.normal(0, c.RATING_NOISE[mt])
            rating = int(np.clip(round(raw), 0, 4))

        if left:
            signal, label, weight = "leave", 0, -1.5
        elif rated:
            signal, label = "join_rated", (1 if rating >= 3 else 0)
            weight = 3.0 if label == 1 else 2.0
        else:
            signal, label, weight = "join_no_rate", 1, 1.0

        ts = ev["end_time"] + timedelta(hours=float(rng.random()))
        rows.append({
            "user_id": int(u), "event_id": int(ev["event_id"]),
            "signal_type": signal, "rating": rating, "label": label,
            "implicit_label": -1 if left else 1, "signal_weight": weight,
            "timestamp": ts, "join_order": order,
            "n_known_in_roster": kt["known"], "n_first_hand_in_roster": kt["first"],
            "known_valence": kt["valence"],
            "organizer_score": state.organizer_score(org),
            "organizer_first_time": 1 if state.organizer_events(org) == 0 else 0,
            **snap,
        })

        # state updates (after snapshot, so features stay point-in-time)
        val = _valence(rating, left)
        if left:
            state.record_leave(u)
        elif rated:
            state.record_rating(u, int(ev["activity_id"]), int(ev["sport_cluster"]), rating)
            state.record_organizer_rating(org, rating)
        else:
            state.record_join_norate(u)

        for v in roster:
            if v == u:
                continue
            state.record_coattendance(u, v, val)
            if val > 0:
                p_follow = float(np.clip(
                    0.15 * float(urow["extraversion"]) * (0.5 + 0.5 * float(urow["agreeableness"])), 0, 1))
                if motivations[v] == mt:
                    p_follow = min(1.0, p_follow * 1.8)
                if not state.follows(u, v, ev["end_time"]) and rng.random() < p_follow:
                    state.add_follow(u, v, time_created=ev["end_time"])
                    if motivations[v] == mt and rng.random() < 0.5:
                        state.add_follow(v, u, time_created=ev["end_time"])
                if rng.random() < 0.10 * max(val, 0):
                    state.add_like(u, v, int(ev["event_id"]), ev["end_time"])
    return rows
