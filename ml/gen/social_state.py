"""Mutable social/history state with point-in-time reads."""
from collections import defaultdict


class SocialState:
    def __init__(self, n_users: int):
        self.n_users = n_users
        self._following = defaultdict(dict)        # u -> {v: time_created}
        self._coattend = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))  # u -> v -> [count, valence_sum]
        self._likes = defaultdict(set)             # u -> {liked v}
        self.like_rows = []                        # (liker, liked, event_id, time)
        self.follow_rows = []                      # (follower, following, time_created)
        self._org_events = defaultdict(int)        # org -> events run
        self._org_rating_sum = defaultdict(float)  # org -> sum ratings received
        self._booked = defaultdict(list)           # u -> [(start, end)]
        # history-so-far
        self._joins = defaultdict(int)
        self._rating_sum = defaultdict(float)
        self._leaves = defaultdict(int)
        self._act_sum = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))   # u -> act -> [n, sum]
        self._clu_sum = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))   # u -> clu -> [n, sum]

    # ---- bookings ----
    def book(self, user, start, end):
        self._booked[user].append((start, end))

    def is_busy(self, user, start, end):
        for (s, e) in self._booked[user]:
            if s < end and start < e:   # strict overlap; back-to-back ok
                return True
        return False

    # ---- follows ----
    def add_follow(self, u, v, time_created):
        if v not in self._following[u]:
            self._following[u][v] = time_created
            self.follow_rows.append((u, v, time_created))

    def follows(self, u, v, as_of):
        t = self._following[u].get(v)
        return t is not None and t <= as_of

    # ---- likes ----
    def add_like(self, u, v, event_id, time):
        if v not in self._likes[u]:
            self._likes[u].add(v)
            self.like_rows.append((u, v, event_id, time))

    def likes(self, u, v):
        return v in self._likes[u]

    # ---- co-attendance ----
    def record_coattendance(self, u, v, valence):
        cell = self._coattend[u][v]
        cell[0] += 1
        cell[1] += valence

    def coattend_valence(self, u, v):
        return self._coattend[u][v][1]

    # ---- organiser stats ----
    def record_organizer_rating(self, org, rating):
        self._org_events[org] += 1
        self._org_rating_sum[org] += rating

    def organizer_score(self, org):
        n = self._org_events[org]
        return (self._org_rating_sum[org] / n) if n else 0.0

    def organizer_events(self, org):
        return self._org_events[org]

    # ---- history-so-far ----
    def record_rating(self, user, activity, cluster, rating):
        self._joins[user] += 1
        self._rating_sum[user] += rating
        a = self._act_sum[user][activity]; a[0] += 1; a[1] += rating
        cl = self._clu_sum[user][cluster]; cl[0] += 1; cl[1] += rating

    def record_join_norate(self, user):
        self._joins[user] += 1

    def record_leave(self, user):
        self._leaves[user] += 1

    def history_snapshot(self, user, activity, cluster):
        j = self._joins[user]
        total_signals = j + self._leaves[user]
        a = self._act_sum[user][activity]
        cl = self._clu_sum[user][cluster]
        return {
            "total_joins": j,
            "avg_rating": (self._rating_sum[user] / j) if j else 0.0,
            "no_show_rate": (self._leaves[user] / total_signals) if total_signals else 0.0,
            "act_affinity": (a[1] / a[0]) if a[0] else 0.0,
            "act_seen_count": a[0],
            "cluster_affinity": (cl[1] / cl[0]) if cl[0] else 0.0,
            "cluster_seen_count": cl[0],
        }


def seed_follows(state, users, rng, frac=0.12):
    """Seed a small pre-timeline follow network for ~frac of all users."""
    import numpy as np
    from ml.gen import config as c

    n = len(users)
    geo = users["geo_cluster"].values
    extr = users["extraversion"].values
    chosen = rng.random(n) < frac
    for u in np.where(chosen)[0]:
        k = int(rng.integers(1, 4))                    # 1-3 follows
        same = np.where(geo == geo[u])[0]
        same = same[same != u]
        pool = same if len(same) >= k else np.delete(np.arange(n), u)
        w = extr[pool] + 0.1
        w = w / w.sum()
        for v in rng.choice(pool, size=min(k, len(pool)), replace=False, p=w):
            state.add_follow(int(u), int(v), time_created=c.START_DATE)
