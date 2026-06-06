"""Personality-activity fit and static (roster-independent) logit terms."""
import numpy as np

from ml.gen import config as c


def personality_fit(O: float, C: float, E: float, N: float, H: float, cluster: int) -> float:
    a = c.CLUSTER_ATTRS[int(cluster)]
    f = c.FIT_COEFFICIENTS
    return (f["O_risk"] * O * a["risk"]
            + f["E_social"] * E * a["social"]
            + f["H_risk"] * H * a["risk"]
            + f["N_risk"] * N * a["risk"]
            + f["C_consistency"] * C * a["consistency"])


def dur_fit(pref_minutes: float, event_hours: float, sigma: float = 45.0) -> float:
    gap = abs(event_hours * 60.0 - pref_minutes)
    return float(np.exp(-0.5 * (gap / sigma) ** 2))


def size_fit(pref_size: float, roster_size: float, capacity: float,
             activity: int, sigma: float = 4.0) -> float:
    if not c.ACTIVITY_FLEXIBLE_SIZE[int(activity)]:
        return 0.0
    gap = abs(roster_size - pref_size)
    return float(-(gap / sigma))


def comp_fit(motivated_by_competition: float, skill_level: int) -> float:
    # 1..5 centred at 3; competitive users prefer higher-skill events
    centred = (motivated_by_competition - 3.0) / 2.0
    return float(centred * (skill_level - 1.5) / 1.5)
