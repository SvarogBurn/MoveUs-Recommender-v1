# Feature-Pipeline Redesign — Design

**Date:** 2026-06-06
**Component:** `ml/features.py` (+ coordinated emissions from `ml/generate_data.py`,
slice-decoupling in `ml/models.py` / `ml/train_neural.py`)
**Status:** Approved — ready for implementation planning
**Related:** [event-timeline simulation design](2026-06-06-event-timeline-simulation-design.md)

## Motivation

`features.py` turns the generator CSVs into ML-ready matrices (user vectors, event
vectors, 20-dim pairwise features). A critical review surfaced correctness and
robustness problems:

1. **Within-train temporal leakage (H1).** `_build_history`, `_build_act_affinity`,
   `_build_cluster_affinity`, `_build_act_join_rate`, `_build_no_show_rate`, and the
   co-attendee sets aggregate over the **entire** train set, then attach to every
   train row regardless of timestamp. A row at time `t` sees the user's own ratings
   from *after* `t`. The model trains on leaked future signal.
2. **Magic-slice coupling (H2).** `train_neural.py` (and a duplicate in `models.py`)
   hard-codes `USER_SIDE_SLICE = slice(0,15)`, `EVENT_SIDE_SLICE = slice(36,57)`.
   Any vector-layout change silently feeds the wrong columns to the NN — no error.
3. **`participation_groups` mismodeled (H3).** Built as size bands; the real enum is
   social-circle tiers. (Fixed in the generator spec.)
4. **Redundant + leaky social recompute (M1).** `co_attendee_affinity` uses global
   co-attendance sets (leaky); the generator now emits correct point-in-time social
   features that should be consumed instead.
5. **Affinity `0` is ambiguous (M2).** `act_affinity`/`cluster_affinity` store mean
   rating with `0` for "never attended" — indistinguishable from a real rating of 0.
6. **Group-size features not gated (M3).** Meaningless for fixed-format sports.
7. **Dead features (M4).** `mutual_follows_attending` and `liked_attendee_count` are
   hard-coded `0`.
8. **Event-vector redundancy (L1).** Activity one-hot ⊃ cluster; EFA `f1..f8` are
   hand-authored per-cluster values, near-collinear with the cluster one-hot.
9. **Unnormalized vectors (L2), stale docstring (L3), per-row Python loops (L4).**

## Decisions (from review)

| Decision | Choice |
|---|---|
| Leakage fix (H1) | **Compute point-in-time in the generator timeline** and emit as columns; `features.py` consumes them |
| Social recompute (M1) | `features.py` **consumes** the generator's point-in-time social/roster columns; no global recompute |
| EFA `f1..f8` (L1) | **Drop** them and `CLUSTER_EFA`; keep the cluster one-hot. Event vector 57→49 dims |
| `liked_attendee_count` (M4) | **Simulate likes** in the generator (mirrors `EventMemberLike`); feature becomes a real point-in-time signal |
| `participation_groups` (H3) | Tier-based (FIRST_HAND/SECOND_HAND/COMMON_INTERESTS), per the generator spec |
| Group-size features (M3) | **Gated by `is_flexible_size`** |
| Magic slices (H2) | **Decouple** — `feature_names.json` emits named index ranges; models read ranges from the manifest |
| Affinity missingness (M2) | **Seen-mask + count** alongside the mean; unseen ≠ rated-0 |
| Normalization (L2) | Fit a `StandardScaler` over the numeric user/event vector dims; save + apply |
| Architecture | `features.py` is a thin, leak-free **assembler** of generator-provided columns |

## Architecture

### 1. Generator emissions (additions to `generate_data.py`)

The chronological sweep already tracks per-user state, so each interaction row can
carry **history-so-far**, snapshotted at the user's decision moment (strictly prior
events only):

- `total_joins`, `avg_rating`, `join_rate_30d`, `act_freq`
- `act_affinity` (mean rating so far for the event's activity) + `act_seen_count`
- `cluster_affinity` (mean rating so far for the event's cluster) + `cluster_seen_count`
- `no_show_rate` (leave fraction so far)

These join the social/roster point-in-time columns already in the generator spec
(`n_known_in_roster`, `n_first_hand_in_roster`, `known_valence`, `mutual_follows`,
`liked_attendee_count`, `pref_tier_match`, `organizer_score`, …).

**Likes** (new): a user may *like* a co-attendee after a **positive** shared event,
biased toward same-motivation / preferred-tier / high-valence mates. Emits:
- `likes.csv` — `liker_id, liked_id, event_id, time_created` (mirrors the backend
  `EventMemberLike`)
- per-interaction `liked_attendee_count` = how many already-joined roster members U
  had liked **before** this event (point-in-time)

**Removed**: `f1..f8` event columns and the `CLUSTER_EFA` table.

### 2. `features.py` as an assembler

`features.py` stops recomputing global aggregates. Instead it:
- reads the generator's point-in-time history/social/like columns straight from
  `interactions.csv` (and the split CSVs),
- assembles them into the pairwise matrix and the user/event vectors,
- fits/saves the scalers, and writes the manifest.

The leaky helpers (`_build_history`, `_build_act_affinity`, `_build_cluster_affinity`,
`_build_act_join_rate`, `_build_no_show_rate`, `_build_coattendee_data`) are
**deleted** — their outputs now arrive precomputed and point-in-time.

### 3. Pairwise features (revised)

Same ~20-slot footprint, with corrected/real sources:

- **Contextual:** activity-in-preferred, skill delta, distance sigmoid, duration
  delta, day/time match. Group-size delta/match **gated by `is_flexible_size`**
  (zeroed/omitted for fixed-format sports).
- **Social (real now):** `n_known_in_roster`, `n_first_hand_in_roster`,
  `n_second_hand_in_roster`, `known_valence`, `mutual_follows_attending`,
  `liked_attendee_count`, `pref_tier_match` — all consumed point-in-time. The old
  `organizer_is_followed` slot is replaced.
- **History (point-in-time):** `act_join_rate`, `cluster_affinity` (+ seen-count),
  `act_affinity` (+ seen-count), `act_frequency`, `no_show_rate`.
- **Quality:** `avg_organizer_rating` (now emergent), `organizer_score`,
  `organizer_first_time`, `skill_diversity`.

Exact final column list is fixed in the implementation plan; the manifest is the
source of truth (Section 6).

### 4. Affinity missingness (M2)

For `act_affinity` / `cluster_affinity`, "never attended" must differ from "rated 0":
- emit a **seen-count** companion column (0 ⇒ unseen),
- impute the affinity for unseen entries with the user's **global mean rating** (or a
  neutral mid value for cold users with no history),
- the count doubles as a confidence signal the models can weight.

### 5. Event vectors → 49 dims

Drop the 8 EFA factors. Keep: activity one-hot (31) + scalars
(`skill_level, max_participants, duration_hours, fill_rate, participant_count`) +
cluster one-hot (8) + `day_of_week, time_of_day` + `skill_diversity,
social_density_cat, avg_organizer_rating`. (`fill_rate`/`participant_count`/
`avg_organizer_rating` are now emergent — see generator spec.)

### 6. User vectors + named manifest (H2)

- `participation` block: **4 → 3 dims** (FIRST_HAND/SECOND_HAND/COMMON_INTERESTS).
  Recompute the total (was 97).
- `feature_names.json` gains a **`ranges`** section mapping logical groups to
  `[start, end)` index spans for both user and event vectors, e.g.
  `{"user": {"prefs": [0,13], "demo": [13,15], "side": [0,15], ...},
    "event": {"side": [...]}}`.
- `train_neural.py` and `models.py` **read slices from the manifest** instead of
  literal `slice(0,15)` / `slice(36,57)`. Dim asserts derive from the manifest too,
  so a layout change can't silently misalign the NN inputs.

### 7. Normalization (L2)

Fit a `StandardScaler` over the **numeric** (non-one-hot) dims of the user and event
vectors, save as `scaler_user.pkl` / `scaler_event.pkl`, and apply on load. NCF's
side projection currently sees raw `age`(16–65) next to 1–5 prefs; this fixes that.
(Two-Tower's `LayerNorm` partially compensates but should use the scaled inputs too.)

### 8. Housekeeping (L3/L4)

- Replace `iterrows` / per-row Python loops (`_build_no_show_rate`, pref-matrix build)
  with vectorised pandas/numpy where they remain.
- Fix the stale top docstring (dims, "v3" notes); regenerate dim numbers from the
  manifest rather than hard-coded asserts.

## Components & responsibilities

| Unit | Responsibility | Depends on |
|---|---|---|
| (generator) point-in-time emit | history/social/like columns per interaction | timeline sweep state |
| (generator) `simulate_likes` | likes.csv + liked_attendee_count | rosters, valence |
| `load_columns` | read precomputed point-in-time columns from CSVs | generator outputs |
| `build_user_vectors` | assemble user vector (3-dim participation) + names | columns |
| `build_event_vectors` | assemble 49-dim event vector + names | events.csv |
| `build_pairwise` | assemble pairwise matrix from precomputed columns | columns |
| `fit_scalers` | pairwise + user + event scalers (fit on train) | matrices |
| `write_manifest` | `feature_names.json` incl. named index `ranges` | names |
| (models) `slices_from_manifest` | derive NN input slices from manifest | manifest |

## Out of scope
- The generator redesign itself (see the related spec). This spec only adds the
  point-in-time history columns, the likes simulation, and the `f1..f8` removal.
- `CLUSTER_ATTRS` / cluster taxonomy provenance (noted out-of-scope in the generator
  spec) is unchanged here; the cluster one-hot is retained as-is.

## Testing

- **No leakage**: each interaction's history columns are a function of strictly
  earlier interactions only (verify against a recomputed point-in-time oracle on a
  small slice).
- **Manifest-driven layout**: NN slices and dim asserts are read from
  `feature_names.json`; a deliberate layout change updates them automatically (no
  magic numbers remain in model code).
- **Real social features**: `mutual_follows_attending` and `liked_attendee_count`
  are non-zero for appropriate rows (not constant 0).
- **Affinity missingness**: unseen activities/clusters have seen-count 0 and an
  imputed (not literal-0) affinity; a genuine rating-0 has seen-count > 0.
- **Gated group-size**: group-size features are inert for fixed-format sports and
  active for flexible ones.
- **EFA removed**: no `f*` columns in the event vector; event dim = 49.
- **Participation tiers**: user-vector participation block is 3 dims over
  FIRST_HAND/SECOND_HAND/COMMON_INTERESTS.
- **Scaler integrity**: user/event/pairwise scalers fit on train only; transform
  applied to test/cold; cold users have all-zero history columns.
