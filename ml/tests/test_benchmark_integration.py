import numpy as np
from ml.models.run_benchmark import run_benchmark


def test_benchmark_runs_on_small_generated_data(tmp_path, small, monkeypatch):
    # generate a small dataset in memory and run the full benchmark
    import ml.gen.io as io
    monkeypatch.setattr(io, "DATA_DIR", tmp_path)
    import numpy as np
    from ml.gen.timeline import run_timeline
    rng = np.random.default_rng(5)
    users, events, interactions, state = run_timeline(rng)
    io.write_all(users, events, interactions, state)

    results = run_benchmark(data_dir=tmp_path, fast=True)
    assert "Random" in results and "FactorizationMachine" in results
    # sanity: at least one learned model beats Random on overall NDCG@10
    learned = [v["overall"]["ndcg@10"] for k, v in results.items() if k != "Random"]
    assert max(learned) >= results["Random"]["overall"]["ndcg@10"]
