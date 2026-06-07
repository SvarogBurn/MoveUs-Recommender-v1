"""Benchmark visualisations."""
from ml.eval.plots import plot_benchmark


def _slice(nd, rc):
    return {"ndcg@10": nd, "recall@10": rc, "mrr": nd, "n": 1000, "pool_size": 53.0}


def _results():
    return {
        "Random":               {"overall": _slice(0.12, 0.23), "warm": _slice(0.12, 0.23), "cold": _slice(0.12, 0.22)},
        "Popularity":           {"overall": _slice(0.15, 0.26), "warm": _slice(0.16, 0.27), "cold": _slice(0.10, 0.18)},
        "FactorizationMachine": {"overall": _slice(0.21, 0.31), "warm": _slice(0.22, 0.32), "cold": _slice(0.17, 0.25)},
    }


def test_plot_benchmark_writes_nonempty_pngs(tmp_path):
    paths = plot_benchmark(_results(), tmp_path)
    assert len(paths) >= 2
    for p in paths:
        assert p.exists() and p.suffix == ".png" and p.stat().st_size > 0


def test_plot_benchmark_handles_missing_random(tmp_path):
    res = _results()
    del res["Random"]                       # must not crash without a Random baseline
    paths = plot_benchmark(res, tmp_path)
    assert all(p.exists() for p in paths)
