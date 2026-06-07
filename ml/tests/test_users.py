import numpy as np
from ml.gen import config as c
from ml.gen.users import generate_users


def test_user_count_and_columns(small, rng):
    df = generate_users(rng)
    assert len(df) == c.N_USERS
    for col in ["user_id", "motivation_type", "frequency_tier", "gender",
                "openness", "conscientiousness", "extraversion", "agreeableness",
                "neuroticism", "hardiness", "acquaintance_preference",
                "preferred_group_size", "participation_groups",
                "organizing_openness", "leadership_inclination"]:
        assert col in df.columns


def test_gender_distribution_weighted(small, rng):
    df = generate_users(rng)
    frac = df["gender"].value_counts(normalize=True)
    assert frac.get(0, 0) > 0.35 and frac.get(1, 0) > 0.35     # majorities
    assert frac.get(2, 0) < 0.08 and frac.get(3, 0) < 0.08     # minorities


def test_participation_groups_only_three_tiers(small, rng):
    df = generate_users(rng)
    for s in df["participation_groups"]:
        vals = {int(x) for x in str(s).split(",") if x != ""}
        assert vals.issubset({0, 1, 2})       # never 3 (ROMANTIC dropped)
        assert len(vals) >= 1


def test_survey_fields_have_spread(small, rng):
    df = generate_users(rng)
    # decoupled fields must vary, not collapse to a constant
    assert df["preferred_group_size"].nunique() > 4
    assert df["acquaintance_preference"].nunique() >= 4


def test_bigfive_population_distribution(small, rng):
    df = generate_users(rng)
    # uniform Normal(0.5, 0.1)-ish: mean near 0.5, modest spread, same for all
    assert 0.4 < df["extraversion"].mean() < 0.6
    assert df["extraversion"].std() < 0.2
