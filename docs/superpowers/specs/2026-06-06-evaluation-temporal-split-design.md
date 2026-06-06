# Evaluation & Temporal-Split Foundation — Design

**Date:** 2026-06-06
**Component:** new `ml/eval/` package; changes to `ml/gen/splits.py` and `ml/features.py`
**Status:** Approved design, pending spec review
**Related:** [generator rewrite spec](2026-06-06-event-timeline-simulation-design.md), [feature-pipeline spec](2026-06-06-feature-pipeline-redesign-design.md), [model-suite spec](2026-06-06-model-suite-design.md)

## Motivation

The current pipeline evaluates with leave-one-out and 99 sampled negatives (LOO@99).
The adopted methodology (Undermind reports) requires the opposite: a **global
temporal split** with **full-catalog ranking** and graded, top-heavy metrics.
Sampled-negative LOO is rejected because it can leak future information and even
reverse model rankings (Cañamares & Castells 2020; Ji et al. 2020; Hidasi & Czapp
2023; Zhao et al. 2020). This spec defines the shared evaluation substrate that
every model in the [model-suite spec](2026-06-06-model-suite-design.md) is trained
and scored against.

## Decisions

| Decision | Choice |
|---|---|
| Split | **Global temporal**: train `< T1`, validation `[T1, T2)`, test `[T2, end)` |
| Default boundaries | ~70 / 15 / 15 by interaction time (quantiles of the timeline); configurable |
| Candidate ranking | **Full catalog** — rank against all feasible events; no sampled negatives |
| Where the split lives | **Eval/feature layer**, not the generator (generator emits full chronological `interactions.csv` + a cold-user holdout flag) |
| Primary metric | **Weighted NDCG@10** (graded gains from the 0–4 outcome) |
| Secondary metric | **Recall@10** |
| Slices | overall, warm-user, cold-user, new-event |
| Legacy | LOO@99 removed; MRR not reported (can be added later as single-target auxiliary) |

## Architecture

### 1. Temporal split (`ml/eval/split.py`)

- Input: `interactions.csv` (full chronological log), `users.csv`, `events.csv`.
- Compute boundaries `T1`, `T2` as time quantiles of the interaction `timestamp`
  column (defaults: 0.70, 0.85). Configurable absolute datetimes override.
- Emit three disjoint, time-ordered partitions of interactions:
  `train` (`ts < T1`), `val` (`T1 ≤ ts < T2`), `test` (`ts ≥ T2`).
- **Strict ordering guarantee:** every train timestamp < every val timestamp <
  every test timestamp.
- Models train on `train` (tune on `val`); final numbers are reported on `test`.
- **Cold users:** the generator's `N_COLD_USERS` holdout is exposed as an
  `is_cold_user` flag on `users.csv`. These users *do* interact across the timeline
  (they shape the social graph — generator decision I2), but the eval layer
  **excludes all their interactions from `train`** so they are profile-only at test
  time. Concretely: `train = { interactions where ts < T1 AND not is_cold_user }`.
  Their test-window positives form the cold evaluation slice.

### 2. Candidate construction (`ml/eval/candidates.py`)

For a given evaluation user `u` and the test window:
- **Relevant set** `R(u)` = events `u` actually attended (positive signal:
  `join_rated` with rating ≥ 1, or `join_no_rate`) whose `timestamp ∈ test`.
  (Graded relevance uses the rating; unrated positive → a small floor gain.)
- **Candidate set** `C(u)` = **all events whose `start_time` falls in the test
  window** that pass the **feasibility filter**, unioned with `R(u)`:
  - not in the past relative to the event's own start (events are upcoming),
  - day/time within `u`'s availability,
  - distance ≤ `u`'s `max_travel_distance`,
  - capacity not exceeded (`participant_count < max_participants`),
  - `u` is not already booked in an overlapping interval (reuse the generator's
    booked-interval notion from the test-window attendance).
- Events `u` interacted with **before** the test window are excluded from `C(u)`
  (already-seen). `R(u) ⊆ C(u)` always.
- Catalog size is ~the test-window event count (low thousands) → full ranking is
  cheap; **no negative sampling**.

### 3. Metrics (`ml/eval/metrics.py`) — defined explicitly

Let a model produce a score for every event in `C(u)`; rank descending.

**Weighted (graded) NDCG@10.** For ranked position `i` (1-indexed) holding event
`e`:
```
gain(e)  = 2**rel(e) - 1            # rel(e) = rating 0..4; rel=0 for non-relevant
                                    # unrated positive -> rel = 1 (floor)
DCG@10   = Σ_{i=1..10} gain(e_i) / log2(i + 1)
IDCG@10  = DCG of R(u) sorted by gain descending, truncated at 10
NDCG@10  = DCG@10 / IDCG@10   (0 if IDCG@10 == 0)
```
Report the mean over evaluation users. (Discount base 2; gain `2^rel − 1`; both
stated to avoid the library-default ambiguity noted by Tamm et al. 2021.)

**Recall@10.**
```
Recall@10 = |{relevant events in top 10}| / |R(u)|     (0 if |R(u)| == 0 excluded)
```
Mean over evaluation users with `|R(u)| ≥ 1`.

### 4. Slices (`ml/eval/slices.py`)

Each metric is reported for:
- **overall** — all evaluation users with ≥1 test-window relevant event.
- **warm** — users with ≥1 interaction in `train`.
- **cold** — users flagged `is_cold_user`, excluded from `train` (profile only at
  test time), evaluated on their test-window relevant events.
- **new-event** — restricted to instances whose **relevant events first appear in
  the test window** (no pre-test interactions for that event); metric computed over
  those relevant events only.

### 5. Harness (`ml/eval/harness.py`)

- `evaluate(model, split, users, events) -> dict` returning
  `{slice: {"ndcg@10": x, "recall@10": y}, ...}` plus per-user raw arrays for
  significance tests.
- A model implements the interface in the [model-suite spec](2026-06-06-model-suite-design.md):
  `fit(train, val, users, events)` and `score(u, candidate_event_ids) -> np.ndarray`.
- The harness builds `C(u)`/`R(u)` once per user, calls `score`, computes metrics,
  aggregates by slice, and writes `ml/results/eval_<model>.json` + a combined
  `ml/results/benchmark.csv` (rows = models, cols = slice×metric).

### 6. Changes to existing code

- **`ml/gen/splits.py`:** remove `build_splits` (LOO) and `ensure_min_joins`
  (min-join was a LOO requirement; temporal eval does not need every warm user to
  have a held-out positive). Keep `finalize_events`. The generator now writes only
  `users.csv` (with `is_cold_user`), `events.csv`, `interactions.csv`, `follows.csv`,
  `likes.csv` — no `train/test/cold_start_users` CSVs.
- **`ml/gen/users.py` / `ml/gen/io.py`:** add an `is_cold_user` boolean column to
  `users.csv` (True for the last `N_COLD_USERS` ids); drop the split-file writes.
- **`ml/features.py`:** consume the temporal `train` partition for fitting
  history/affinity (already point-in-time), and expose feature builders the models
  call at score time for arbitrary `(u, e)` pairs (the existing
  `build_pairwise_for_pairs` pattern, adapted to the temporal split).

## Components & responsibilities

| Unit | Responsibility |
|---|---|
| `ml/eval/split.py` | temporal partition of interactions; boundary computation |
| `ml/eval/candidates.py` | per-user relevant set + feasible full-catalog candidates |
| `ml/eval/metrics.py` | weighted NDCG@10, Recall@10 (explicit formulas) |
| `ml/eval/slices.py` | warm / cold / new-event / overall partitioning of users & events |
| `ml/eval/harness.py` | run a model through the protocol; emit results |
| `ml/gen/splits.py` | (reduced) finalize_events only |
| `ml/features.py` | history/features from `train`; score-time pair features |

## Testing

- **Strict temporal order:** max(train.ts) < min(val.ts) ≤ max(val.ts) < min(test.ts).
- **No leakage:** no candidate or feature for a test instance uses data with
  `ts ≥ T2` except the held-out label itself.
- **Feasibility:** every candidate in `C(u)` passes all hard constraints; `R(u) ⊆ C(u)`.
- **Full catalog:** candidate count per user ≈ feasible test-window events (not 100).
- **NDCG correctness:** unit tests on hand-computed tiny rankings (e.g. a single
  rel=4 at rank 1 → NDCG 1.0; at rank 2 → 1/log2(3) normalised).
- **Recall correctness:** hand-checked small cases incl. multi-relevant.
- **Slices partition:** warm ∪ cold = all evaluated users; new-event instances are a
  subset; counts reported.
- **Cold definition:** `is_cold_user` users have zero `train` interactions.

## Out of scope
- The models themselves (see model-suite spec).
- LambdaFM and MRR (deferred).
