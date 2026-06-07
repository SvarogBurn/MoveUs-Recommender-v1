# Model Suite — Design

**Date:** 2026-06-06
**Component:** new `ml/models/` package (rewrite of `ml/models.py`); depends on the
[evaluation & temporal-split foundation](2026-06-06-evaluation-temporal-split-design.md)
**Status:** Approved design, pending spec review

## Motivation

Replace the current ad-hoc model list (GNB / RF / SVD / kNN / NCF / two-tower /
XGBoost / hybrids, evaluated with LOO@99) with a compact, literature-backed,
**staged** benchmark that matches the MoveUs task: profile-only cold start at
launch, interaction-driven personalisation later, top-list output. Every model is
trained on the temporal `train` split and graded by the shared harness
(Weighted NDCG@10, Recall@10, with warm/cold/new-event slices).

## Decisions

| Decision | Choice |
|---|---|
| Model set | Random; Popularity+feasibility; Logistic Regression; LightGBM-LambdaMART; Factorization Machines; BPR-MF; LightGCN; DeepFM |
| Deferred | LambdaFM (optional stretch, separate later cycle) |
| Framing | Event **ranking** (not rating regression); 0–4 outcome = graded relevance |
| Training data | temporal `train` split; `val` for early-stopping / tuning |
| Scoring | each model scores full feasible candidate set per user (harness-driven) |
| Cold/new-event fallback | ID-only models (BPR-MF, LightGCN) fall back to the popularity+feasibility score for unseen users/events |

## Common interface

```python
class Recommender:
    name: str
    def fit(self, ctx: TrainContext) -> None: ...
    def score(self, user_id: int, candidate_event_ids: np.ndarray) -> np.ndarray: ...
```
`TrainContext` bundles: `train` interactions, `users`, `events`, the fitted
feature builders (user vectors, event vectors, pairwise builder) and the follow /
co-attendance / likes graphs — all restricted to `ts < T1`. `score` returns one
real value per candidate (higher = more relevant). The harness handles ranking,
metrics, and slicing, so models never see the test data.

## Models

### Baselines
- **Random** (`models/random_rec.py`): `score` returns uniform noise. Lower bound.
- **Popularity + feasibility** (`models/popularity.py`): candidates are already
  feasible (harness filter); score = normalised train attendance count, blended
  with recency (more recent events up-weighted) and coarse activity-cluster match
  to the user's preferred clusters. Serves as the fallback for ID-only models.

### Tabular (feature-driven, cold-start capable)
- **Logistic Regression** (`models/logreg.py`): pointwise `sklearn`
  `LogisticRegression` on the standardised pairwise feature matrix; binary target
  = positive attendance (rating ≥ 3 or unrated-positive); `score` = predicted
  probability. Transparent baseline.
- **LightGBM-LambdaMART** (`models/lgbm_ranker.py`): `lightgbm.LGBMRanker`,
  `objective="lambdarank"`, `eval_metric="ndcg"`, groups = per-user, graded label
  from the 0–4 rating; features = pairwise user–event matrix. Early-stop on `val`
  NDCG@10. Main tabular ranker.

### Hybrid / cold-start
- **Factorization Machines** (`models/fm.py`): a PyTorch FM over a sparse feature
  vector concatenating user fields, event fields, and context (activity, cluster,
  time slot, roster/known-face features). First-order weights + factorised pairwise
  interactions; logistic loss on positive/negative pairs sampled from `train`.
  (Library `xlearn`/`lightfm` acceptable if reproducible; default = our small torch
  FM for control.) Main cold-start model.

### Collaborative (warm-start)
- **BPR-MF** (`models/bpr_mf.py`): id-based user/event embeddings, Bayesian
  Personalized Ranking loss over `train` implicit positives vs sampled negatives.
  `score` = user·event dot product; unseen user/event → popularity fallback.
- **LightGCN** (`models/lightgcn.py`): light graph convolution over the user–event
  bipartite graph built from `train` joins; follow + co-attendance edges folded in
  as additional relations. Layer-averaged embeddings; BPR loss. `score` = dot
  product; unseen nodes → popularity fallback.

### Neural hybrid
- **DeepFM** (`models/deepfm.py`): FM component + deep MLP over the same sparse
  feature representation as the FM model; sigmoid output trained with weighted BCE
  on positives/negatives. The neural slot — tests whether a higher-capacity learner
  exploits the synthetic structure beyond FM / LightGBM.

## Feature access per model (from the methodology)

| Feature | LogReg | LightGBM | FM | DeepFM | BPR-MF | LightGCN |
|---|---|---|---|---|---|---|
| user profile / survey | ✓ | ✓ | ✓ | ✓ | – | (side) |
| event metadata | ✓ | ✓ | ✓ | ✓ | – | (side) |
| time/location/skill match | ✓ | ✓ | ✓ | ✓ | eng. | eng. |
| roster / known-face context | ✓ | ✓ | ✓ | ✓ | – | – |
| join/rating history | limited | ✓ | ✓ | ✓ | core | core |
| social graph | eng. | eng. | eng. | eng. | – | strong |

All point-in-time, taken from `train` only (the feature pipeline already enforces
this), so no model sees the future.

## Orchestration & output

- `ml/models/registry.py`: list of model factories.
- `ml/models/run_benchmark.py`: load data → build temporal split (eval foundation)
  → build `TrainContext` from `train` → for each model: `fit`, then
  `harness.evaluate` → collect rows.
- Outputs: `ml/results/benchmark.csv` (model × {overall,warm,cold,new-event} ×
  {NDCG@10, Recall@10}), `ml/results/eval_<model>.json`, and a grouped bar chart
  `ml/results/benchmark_ndcg.png`.
- Trained artifacts saved under `ml/models_store/` (kept separate from the code
  package `ml/models/`).

## Components & responsibilities

| Unit | Responsibility |
|---|---|
| `ml/models/base.py` | `Recommender` interface + `TrainContext` |
| `ml/models/{random_rec,popularity,logreg,lgbm_ranker,fm,bpr_mf,lightgcn,deepfm}.py` | one model each |
| `ml/models/registry.py` | model factory list |
| `ml/models/run_benchmark.py` | end-to-end benchmark run + results |

## Testing

- **Interface conformance:** each model implements `fit`/`score`; `score` returns
  a finite array of length = #candidates.
- **Random < learned:** the random baseline's NDCG@10 is below every learned model
  (sanity that signal is learned, on a small synthetic run).
- **Popularity beaten:** at least the strong models (FM / LightGBM / DeepFM) beat
  popularity+feasibility overall (smoke threshold, not a hard gate).
- **Cold-start behaviour:** FM/DeepFM/LogReg/LightGBM produce non-degenerate cold
  scores; BPR-MF/LightGCN fall back to popularity for cold users/new events
  (verify fallback path is exercised, not NaNs).
- **Determinism:** fixed seeds → reproducible benchmark.csv within tolerance.
- **No leakage:** models receive only `train`-restricted `TrainContext`
  (assert no `ts ≥ T1` rows reach `fit`).

## Out of scope
- LambdaFM (later optional cycle).
- Production/Django serving integration (separate from this offline benchmark).
- Hyperparameter search beyond light `val`-based early stopping / a small grid.
