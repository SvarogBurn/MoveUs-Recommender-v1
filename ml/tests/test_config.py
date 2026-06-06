import numpy as np
from ml.gen import config as c


def test_archetype_fractions_sum_to_one():
    assert abs(sum(c.MOTIVATION_ARCHETYPES.values()) - 1.0) < 1e-9


def test_freq_tier_dist_rows_sum_to_one():
    for mt, dist in c.FREQ_TIER_DIST.items():
        assert abs(sum(dist.values()) - 1.0) < 1e-9, mt


def test_gender_weights_minorities_small_and_sum_one():
    w = c.GENDER_WEIGHTS  # [MALE, FEMALE, NON_BINARY, PREFER_NOT_TO_SAY]
    assert abs(sum(w) - 1.0) < 1e-9
    assert w[0] > 0.4 and w[1] > 0.4
    assert w[2] < 0.05 and w[3] < 0.05


def test_fit_coefficients_match_table_17_verbatim():
    f = c.FIT_COEFFICIENTS
    assert f["O_risk"] == 0.42      # Openness x Risk tolerance [84]
    assert f["E_social"] == 0.42    # Extraversion x Social interaction [96]
    assert f["H_risk"] == 0.75      # Hardiness x Risk tolerance [103]
    assert f["N_risk"] == -0.47     # Neuroticism x Risk tolerance [84]
    # conscientiousness x consistency: theoretical (no Table-17 number)
    assert 0.0 <= f["C_consistency"] <= 0.5


def test_every_activity_has_cluster_and_flexible_flag():
    assert set(c.ACTIVITY_CLUSTER.keys()) == set(range(31))
    assert set(c.ACTIVITY_FLEXIBLE_SIZE.keys()) == set(range(31))
    # fixed-format sports are not flexible
    assert c.ACTIVITY_FLEXIBLE_SIZE[2] is False   # SOCCER
    assert c.ACTIVITY_FLEXIBLE_SIZE[3] is False   # TENNIS
    assert c.ACTIVITY_FLEXIBLE_SIZE[0] is True    # HIKING


def test_cluster_attrs_cover_eight_clusters():
    assert set(c.CLUSTER_ATTRS.keys()) == set(range(8))
    for a in c.CLUSTER_ATTRS.values():
        assert set(a.keys()) == {"risk", "consistency", "social", "injury"}
