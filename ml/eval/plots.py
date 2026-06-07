"""Benchmark visualisations: model comparison, per-slice, and lift-over-random.

Headless-safe (Agg backend) so it runs on Kaggle / CI without a display.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SLICES = ["overall", "warm", "cold"]


def _ndcg(results, model, sl="overall"):
    return float(results[model].get(sl, {}).get("ndcg@10", 0.0))


def _recall(results, model, sl="overall"):
    return float(results[model].get(sl, {}).get("recall@10", 0.0))


def plot_benchmark(results: dict, out_dir) -> list:
    """Write benchmark charts as PNGs into ``out_dir``; return the paths written."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # order models by overall NDCG@10 (best first), keep Random visible for reference
    models = sorted(results.keys(), key=lambda m: _ndcg(results, m), reverse=True)
    rnd = _ndcg(results, "Random") if "Random" in results else None
    paths = []

    # 1) Overall NDCG@10 vs Recall@10, grouped bars, with Random reference line
    fig, ax = plt.subplots(figsize=(max(7, 1.1 * len(models)), 4.5))
    x = np.arange(len(models)); w = 0.38
    ax.bar(x - w / 2, [_ndcg(results, m) for m in models], w, label="NDCG@10", color="#3b7dd8")
    ax.bar(x + w / 2, [_recall(results, m) for m in models], w, label="Recall@10", color="#e07b39")
    if rnd is not None:
        ax.axhline(rnd, ls="--", lw=1, color="#888",
                   label=f"Random NDCG@10 ({rnd:.3f})")
    ax.set_xticks(x); ax.set_xticklabels(models, rotation=30, ha="right")
    ax.set_ylabel("score"); ax.set_title("Overall ranking quality by model")
    ax.legend(); fig.tight_layout()
    p = out_dir / "overall_metrics.png"; fig.savefig(p, dpi=130); plt.close(fig); paths.append(p)

    # 2) NDCG@10 per model across slices (overall / warm / cold)
    fig, ax = plt.subplots(figsize=(max(7, 1.1 * len(models)), 4.5))
    x = np.arange(len(models)); w = 0.26
    colors = {"overall": "#444", "warm": "#d1495b", "cold": "#2a9d8f"}
    for i, sl in enumerate(SLICES):
        ax.bar(x + (i - 1) * w, [_ndcg(results, m, sl) for m in models], w,
               label=sl, color=colors[sl])
    ax.set_xticks(x); ax.set_xticklabels(models, rotation=30, ha="right")
    ax.set_ylabel("NDCG@10"); ax.set_title("NDCG@10 by evaluation slice")
    ax.legend(); fig.tight_layout()
    p = out_dir / "slice_ndcg.png"; fig.savefig(p, dpi=130); plt.close(fig); paths.append(p)

    # 3) Lift over Random (only meaningful when a Random baseline is present)
    if rnd is not None:
        learned = [m for m in models if m != "Random"]
        lift = [_ndcg(results, m) - rnd for m in learned]
        fig, ax = plt.subplots(figsize=(max(7, 1.1 * len(learned)), 4.5))
        xl = np.arange(len(learned))
        ax.bar(xl, lift, color=["#2a9d8f" if v > 0 else "#c0504d" for v in lift])
        ax.axhline(0, color="#333", lw=1)
        ax.set_ylabel("NDCG@10 lift over Random")
        ax.set_title("How much each model beats the Random baseline")
        ax.set_xticks(xl); ax.set_xticklabels(learned, rotation=30, ha="right")
        fig.tight_layout()
        p = out_dir / "lift_over_random.png"; fig.savefig(p, dpi=130); plt.close(fig); paths.append(p)

    return paths
