"""End-to-end benchmark: load data -> temporal split -> context -> models -> harness."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ml.eval.split import temporal_split
from ml.eval.harness import evaluate, EvalData
from ml.models.base import TrainContext
from ml.models.context import build_feature_context
from ml.models.registry import all_models

DATA_DIR_DEFAULT = Path(__file__).resolve().parent.parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


def run_benchmark(data_dir=None, fast: bool = False) -> dict:
    data_dir = Path(data_dir) if data_dir else DATA_DIR_DEFAULT
    users = pd.read_csv(data_dir / "users.csv")
    events = pd.read_csv(data_dir / "events.csv", parse_dates=["start_time", "end_time"])
    inter = pd.read_csv(data_dir / "interactions.csv", parse_dates=["timestamp"])

    # enrich interactions with event activity/cluster metadata needed by context.py
    if "activity_id" not in inter.columns or "sport_cluster" not in inter.columns:
        ev_meta = events[["event_id", "activity_id", "sport_cluster"]]
        inter = inter.merge(ev_meta, on="event_id", how="left")

    train, val, test, _ = temporal_split(inter, users)
    fc = build_feature_context(train, users, events)
    ctx = TrainContext(users=users, events=events, train=train, features=fc)
    data = EvalData(users=users, events=events, train=train, val=val, test=test)

    results = {}
    for model in all_models(fast=fast):
        model.fit(ctx)
        results[model.name] = evaluate(model, data)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "benchmark.json", "w") as fh:
        json.dump(results, fh, indent=2)
    rows = []
    for name, r in results.items():
        row = {"model": name}
        for sl, m in r.items():
            row[f"{sl}_ndcg@10"] = round(m["ndcg@10"], 4)
            row[f"{sl}_recall@10"] = round(m["recall@10"], 4)
            row[f"{sl}_mrr"] = round(m["mrr"], 4)
        rows.append(row)
    pd.DataFrame(rows).to_csv(RESULTS_DIR / "benchmark.csv", index=False)
    return results


def main():
    import pickle
    res = run_benchmark()
    
    # Save best model by NDCG@10 (overall slice)
    best_model_name = None
    best_ndcg = -1.0
    best_model_obj = None
    
    for model_name, metrics in res.items():
        ndcg = metrics.get("overall", {}).get("ndcg@10", 0.0)
        if ndcg > best_ndcg:
            best_ndcg = ndcg
            best_model_name = model_name
    
    if best_model_name:
        # Re-train best model to export it
        models_store = Path(__file__).resolve().parent.parent / "models_store"
        models_store.mkdir(parents=True, exist_ok=True)
        
        # Note: In production, we'd save the already-trained model
        # For now, save metadata for the recommender service
        with open(models_store / "best_model_metadata.txt", "w") as f:
            f.write(f"{best_model_name}\nNDCG@10: {best_ndcg:.4f}")
        
        print(f"\n✓ Best model: {best_model_name} (NDCG@10: {best_ndcg:.4f})")
    
    print(pd.read_csv(RESULTS_DIR / "benchmark.csv").to_string(index=False))


if __name__ == "__main__":
    main()
