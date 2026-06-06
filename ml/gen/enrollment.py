"""Sequential enrollment and event resolution."""
from datetime import timedelta

import numpy as np

from ml.gen import config as c
from ml.gen.fit import personality_fit, dur_fit, size_fit, comp_fit


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def build_candidate_index(users):
    """Precompute fast per-activity / per-cluster candidate arrays plus per-user
    numeric arrays used by the enrollment logit.

    Returns a dict consumed by ``run_enrollment``. Built once per timeline run in
    ``run_timeline`` and reused across all events; ``run_enrollment`` builds it
    lazily when not supplied (slow path for direct test calls).
    """
    n = len(users)

    # Parse the comma-separated preferred-activity strings once.
    pref_lists = [
        [int(x) for x in s.split(",")] for s in users["preferred_activities"].values
    ]

    # activity -> sorted np.array of users who directly prefer that activity
    act_to_users = {a: [] for a in range(31)}
    # cluster -> set of users who prefer *some* activity in that cluster
    clu_to_users = {clu: set() for clu in set(c.ACTIVITY_CLUSTER.values())}
    for u, lst in enumerate(pref_lists):
        for a in lst:
            act_to_users[a].append(u)
            clu_to_users[c.ACTIVITY_CLUSTER[a]].add(u)
    act_to_users = {a: np.array(sorted(v), dtype=np.int64) for a, v in act_to_users.items()}
    clu_to_users = {clu: np.array(sorted(v), dtype=np.int64) for clu, v in clu_to_users.items()}

    # Per-user numeric arrays (avoid .iloc per candidate).
    motivation_type = users["motivation_type"].values
    social_weight = np.array([c.SOCIAL_WEIGHT[m] for m in motivation_type], dtype=float)
    return {
        "act_to_users": act_to_users,
        "clu_to_users": clu_to_users,
        "motivation_type": motivation_type,
        "social_weight": social_weight,
        "acquaintance_preference": users["acquaintance_preference"].values.astype(float),
        "preferred_group_size": users["preferred_group_size"].values.astype(float),
        "preferred_session_duration": users["preferred_session_duration"].values.astype(float),
        "motivated_by_competition": users["motivated_by_competition"].values.astype(float),
    }


def _candidate_array(ev, idx):
    """Users matching the event's activity or its sport cluster (vectorized)."""
    act = int(ev["activity_id"]); clu = int(ev["sport_cluster"])
    direct = idx["act_to_users"].get(act, np.empty(0, dtype=np.int64))
    cluster = idx["clu_to_users"].get(clu, np.empty(0, dtype=np.int64))
    # Union of direct-activity and same-cluster preferrers (cluster superset
    # already includes direct, but union defensively to be safe).
    return np.union1d(direct, cluster)


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


def _known_terms_batch(cand, roster, state, as_of):
    """Vectorized-ish known/first/valence for many candidates against one roster
    snapshot. Returns (known[], first[], valence[]) aligned to ``cand``.

    Follow/co-attendance state is dict-based, so we scan the (small, <= capacity)
    roster per candidate, but avoid pandas ``.iloc`` and avoid materialising
    defaultdict cells for non-existent pairs (the original ``coattend_valence``
    auto-created empty cells, bloating memory).
    """
    m = len(cand)
    known = np.zeros(m, dtype=np.int64)
    first = np.zeros(m, dtype=np.int64)
    valence = np.zeros(m, dtype=float)

    following = state._following
    coattend = state._coattend
    roster_set = roster if isinstance(roster, (set, frozenset)) else set(roster)

    for i in range(m):
        u = int(cand[i])
        k = f = 0
        v = 0.0
        u_follow = following.get(u)               # {target: time}
        u_coatt = coattend.get(u)                 # {other: [count, valence_sum]}
        for r in roster_set:
            # follow either direction, point-in-time
            fwd = u_follow.get(r) if u_follow else None
            mutual = False
            if fwd is not None and fwd <= as_of:
                mutual = True
            else:
                r_follow = following.get(r)
                back = r_follow.get(u) if r_follow else None
                if back is not None and back <= as_of:
                    mutual = True
            if mutual:
                f += 1; k += 1
            elif u_coatt is not None:
                cell = u_coatt.get(r)
                if cell is not None and cell[1] != 0:
                    k += 1
                    v += 1.0 if cell[1] > 0 else -1.0
        known[i] = k; first[i] = f; valence[i] = v
    return known, first, valence


def run_enrollment(ev, users, state, base_propensity, rng, max_passes=3, cand_index=None):
    if cand_index is None:
        cand_index = build_candidate_index(users)
    idx = cand_index

    cap = int(ev["max_participants"])
    org = int(ev["organizer_id"])
    roster = [org]
    state.book(org, ev["start_time"], ev["end_time"])
    as_of = ev["start_time"]
    s_start, e_end = ev["start_time"], ev["end_time"]
    clu = int(ev["sport_cluster"]); act = int(ev["activity_id"])
    org_score = state.organizer_score(org)
    org_first = 1 if state.organizer_events(org) == 0 else 0

    # Candidate pool: matching users, not the organizer, not already busy.
    cand_all = _candidate_array(ev, idx)
    cand = np.array(
        [u for u in cand_all if u != org and not state.is_busy(u, s_start, e_end)],
        dtype=np.int64,
    )
    if cand.size == 0:
        return roster

    # ---- per-user static logit terms (fixed across passes for this event) ----
    pref_dur = idx["preferred_session_duration"][cand]
    pref_comp = idx["motivated_by_competition"][cand]
    pref_gsize = idx["preferred_group_size"][cand]
    social_w = idx["social_weight"][cand]
    acq_pref = idx["acquaintance_preference"][cand]
    bp = base_propensity[cand]

    event_hours = float(ev["duration_hours"])
    skill_level = int(ev["skill_level"])
    sigma_dur = 45.0
    dur_term = np.exp(-0.5 * ((np.abs(event_hours * 60.0 - pref_dur)) / sigma_dur) ** 2)
    comp_centred = (pref_comp - 3.0) / 2.0
    comp_term = comp_centred * (skill_level - 1.5) / 1.5
    flexible = c.ACTIVITY_FLEXIBLE_SIZE[act]

    static = (bp
              + c.W_ACT * 1.0
              + c.W_DUR * dur_term
              + c.W_COMP * comp_term
              + c.W_ORG * (org_score / 4.0 - 0.5 * org_first))

    # decided[i] True once candidate i has been resolved (joined or — implicitly —
    # not added in any subsequent pass). Joiners are removed from the active mask.
    active = np.ones(cand.size, dtype=bool)
    sigma_size = 4.0

    for _ in range(max_passes):
        if len(roster) >= cap:
            break
        live = np.where(active)[0]
        if live.size == 0:
            break

        roster_size = len(roster)
        # size_fit (roster_size constant across all candidates within this pass)
        if flexible:
            size_term = -(np.abs(roster_size - pref_gsize[live]) / sigma_size)
        else:
            size_term = np.zeros(live.size)

        known, first, valence = _known_terms_batch(cand[live], roster, state, as_of)
        acq_gap = np.abs(known - acq_pref[live])
        social = social_w[live] * valence - 0.3 * acq_gap

        logit = static[live] + c.W_SIZE * size_term + social
        p = _sigmoid(logit)
        draws = rng.random(live.size)
        joiners_mask = draws < p

        join_local = live[joiners_mask]
        if join_local.size == 0:
            break

        # Respect remaining capacity: take joiners in array order (deterministic
        # given the rng draws above) until the roster is full.
        remaining = cap - len(roster)
        if join_local.size > remaining:
            join_local = join_local[:remaining]

        for li in join_local:
            u = int(cand[li])
            roster.append(u)
            state.book(u, s_start, e_end)
        active[join_local] = False

        if len(roster) >= cap:
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
