# Event-Timeline Interaction Simulation — Design

**Date:** 2026-06-06
**Component:** `ml/generate_data.py`
**Status:** Approved — ready for implementation planning

## Motivation

The current generator (`ml/generate_data.py`) samples each user's events
independently in a single batch. This has three problems the thesis work wants
to fix:

1. **The social signal is wrong.** It boosts an event when the user *follows the
   organiser* (`organizer_is_followed`, `W_SOCIAL`). In reality, what pulls a
   person in is **how many people they already know are signed up** — and whether
   past experiences with those people were good or bad.
2. **No notion of who joined before whom.** Without temporal join order you
   cannot compute "known attendees already in the event" or "past interactions
   with people in this event."
3. **Per-archetype Big Five is unsupported.** `ARCHETYPE_PERSONALITY` assigns
   each motivation archetype its own Beta-distributed personality. There is no
   research backing these distributions; the thesis itself used a single
   `Normal(0.5, 0.1)` for all Big Five traits (`syntheticdata.txt` §2.1.2).

This redesign moves the generator to a **chronological event-timeline
simulation** where users join events one-by-one, making the roster and all
shared history well-defined at each decision point.

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Architecture | Full event-timeline sim (chronological sweep, one-by-one joins) |
| "Known attendee" sources | Follow relationship **∪** co-attendance history |
| History sentiment | Valence-weighted (good shared history attracts, bad repels) |
| Locality as "knowing" | **No** |
| Follow network timing | **Seed + growth** — a small seed network pre-exists; the rest form over the timeline from positive co-attendance. `follows.csv` is a timestamped sim **output** (seed edges + grown edges) |
| Follow seed | ~10–15% of **all** users start with 1–3 follows, including a small slice of cold users (models "joined because a friend invited me"). Plain `Follow` edges, no pending/request state |
| Cold-user participation (I2) | Cold users join events and **feed warm users' social state** like anyone else (single realistic timeline). Evaluation-purity caveat noted in thesis |
| Event attendance fields (B1/B2) | **Emergent** — `fill_rate`, `participant_count`, `social_density_cat`, `avg_organizer_rating` computed from the actual roster after the sweep, not pre-baked |
| Zero-join warm users (B3) | **Force ≥1 join** — any warm user with no rated interaction gets one synthesized join to their best-matching event, preserving the LOO guarantee |
| Frequency tier semantics | Soft propensity (expected count ≈ old tier, not exact) |
| Organizer reputation ingredients | Past valence + global organizer score + first-time penalty |
| Old `organizer_is_followed` boost | **Removed** |
| Big Five | Single `Normal(0.5, 0.1)` for all users; per-archetype Beta deleted |
| Motivation archetypes | Keep all 4 as **behavioral-only** profiles |
| Candidate pool | Prefiltered by activity/geo match (cost control) |
| Survey fields made causal | `acquaintance_preference`, `preferred_group_size`, `participation_groups`, `enjoys_meeting_new_people`, `activity_vs_social`, `motivated_by_competition` now drive matching/rating (today they're generated but inert) |
| `acquaintance_preference` semantics | **Target/ideal** count of familiar faces — both too-few and too-many known attendees reduce fit |
| Survey-field generation | **Decoupled** — drawn from their own broad distributions, independent of the (now-flat) Big Five, so they carry real, learnable variation |
| Motivation homophily | Same-motivation roster mates stochastically boost U's **rating** and **follow-formation** (same-type positive pairs more likely to become **mutual** follows); applies to all 4 archetypes |

## Architecture

### 1. Personality & archetypes

- **Big Five (`O,C,E,A,N,H`)**: one `Normal(0.5, 0.1)` clipped to `[0,1]`,
  identical distribution for every user. Delete `ARCHETYPE_PERSONALITY` and the
  per-archetype Beta sampling loop in `generate_users`.
- **Motivation archetypes** remain (`competitive`, `casual_recreational`,
  `social`, `unmotivated`) and continue to drive **behavioral** parameters only:
  `RATE_PROB`, `LEAVE_PROB`, `FREQ_TIER_DIST`, and `SOCIAL_WEIGHT`. Personality
  and motivation are now independent axes.
- `SOCIAL_WEIGHT[archetype]` now scales the **known-attendees** signal instead of
  the organiser-follow signal.
- **Survey-preference fields are decoupled from Big Five.** Because Big Five is
  now flat, fields previously derived from it (`acquaintance_preference`,
  `preferred_group_size`, `participation_groups`, `enjoys_meeting_new_people`,
  `activity_vs_social`, `motivated_by_competition`) would collapse toward
  constants. Instead each is drawn from its **own broad distribution** in
  `generate_users`, giving genuine per-user spread. These mirror the frontend
  survey (`moveus-web/src/surveys/preferences-survey.ts`) so the simulator's
  causal inputs match what the real app actually collects.

### 2. Main loop — chronological sweep

```
sort events by start_time ascending
for each event E in time order:
    roster        = [organizer(E)]
    candidates    = prefilter(warm + cold users by activity/geo match to E)
    capacity      = max_participants(E)
    repeat passes (until capacity reached OR a pass adds < epsilon new joins):
        for U in shuffle(undecided candidates):
            if len(roster) >= capacity: break
            p = sigmoid( base_propensity(U)
                       + w_act(U)  * match(U, E)              # activity-vs-social blend
                       + w_soc(U)  * social_block(U, roster)  # known/unknown + valence
                       + group_fit(U, E, roster)             # group-size / participation
                       + comp_fit(U, E)                      # motivated_by_competition
                       + W_ORG     * organizer_rep(U, E) )
            if bernoulli(p):
                add U to roster, record join order + decision timestamp
    resolve E (ratings / leaves) for all roster members except organiser
    update accumulating state (below)
```

Joins update the roster **mid-pass**, so a friend joining earlier in a pass can
trigger later joins → social cascades emerge naturally.

### 3. Signals

**`match(U, E)`** — unchanged components from today's `_join_probs`: activity/
cluster match, skill compatibility, distance, availability, personality-fit.
(`W_ACT, W_SKILL, W_DIST, W_AVAIL, W_PERS` retained.)

**`social_block(U, roster)`** — combines familiarity, acquaintance-preference fit,
the new-people pull, and `SOCIAL_WEIGHT`. Built from three counts over the
already-joined members `m`:

- **`known(U, m)`** = `1` if `U` follows `m` **as of the current event's time**
  (or `m` follows `U`), else a `co_attend_valence(U, m)` term for prior
  co-attendees (positive if shared history was good, negative if bad). Only
  follow edges created *before* this event's `start_time` count — the signal
  respects follow-time.
- **`known_count`** = number of roster members U knows (follow or prior
  co-attendance); **`unknown_count`** = the rest.

These feed:
- **Acquaintance-target fit** — `acquaintance_preference` maps to a target count
  of familiar faces (`Nobody→0, One→1, Two→2, ThreePlus→~3–4, Everyone→whole
  roster`). Fit **peaks at the target and falls off in BOTH directions**:
  `acq_fit = −β · |known_count − target(U)|`. A "Nobody" user is actively
  repelled by a friend-packed event; an "Everyone" user is unsatisfied by
  strangers.
- **New-people pull** — `+ γ · enjoys_meeting_new_people(U) · f(unknown_count)`:
  high scorers are drawn to events full of strangers.
- **Valence familiarity** — `SOCIAL_WEIGHT[archetype(U)] · Σ_m known(U, m)`: the
  running quality of who U knows in the room.

`social_block = acq_fit + new_people_pull + valence_familiarity`.

Note on overlap: a follow edge and positive co-attendance can both apply to the
same pair — intended. The follow is the stronger, persistent tie; valence is the
running quality of shared history.

**`organizer_rep(U, E)`** — secondary, smaller weight `W_ORG` (≪ social weight):
- `past_valence(U, organizer(E))` — U's personal history with this organiser
- `global_organizer_score(organizer)` — running mean of ratings this organiser's
  past events received (centred so neutral ≈ 0)
- `first_time_penalty` — small negative if organiser has run 0 prior events

The organiser also sits in the roster as `roster[0]`, so a joiner's history with
them additionally surfaces through `social_block`. This overlap is intended and
mild given `W_ORG ≪ SOCIAL_WEIGHT`; `organizer_rep` adds the *public-reputation*
and *first-time* signals that co-attendance alone doesn't carry.

**`w_act(U)` / `w_soc(U)`** — the activity-vs-social blend from
`activity_vs_social` (1–5). It is normalised to `s ∈ [0,1]` and split so an
activity-driven user weights `match` more and a socially-driven user weights
`social_block` more (`w_act = 1 − λ·s`, `w_soc = λ·s`, with the exact slope a
tunable constant). One knob, two opposing pulls. *(Direction of the 1–5 scale to
be confirmed against the `scaleActivitySocial` translation strings at
implementation time.)*

**`group_fit(U, E, roster)`** — from `preferred_group_size` and the multi-hot
`participation_groups` (SOLO / PAIR / SMALL / LARGE). Compares U's preferred
size/format against the event's **capacity and current roster size**: a
small-group preferrer is penalised for large events and vice-versa; a SOLO-only
user is penalised for big rosters. Gaussian-style penalty on
`|current_or_expected_size − preferred_group_size|`, zeroed when the event's size
band is in U's `participation_groups` set.

**`comp_fit(U, E)`** — from `motivated_by_competition` (1–5): competition-hungry
users get a positive term on higher-`skill_level` / higher-`competitive`-cluster
events and a mild penalty on very casual ones; low scorers are indifferent. Also
feeds the rating (Section 4).

### 4. Accumulating state

- **Co-attendance map**: sparse `{(u, other) -> [count, valence_sum]}`, updated
  after each event resolves. Only materialised for pairs that actually co-attend.
- **Follow set**: directed `{u -> set(following)}` plus an append log of
  `(follower, following, time_created)` rows. **Pre-seeded** by
  `seed_follows` (below); additional edges are earned over the timeline.
- **Organizer stats**: `{organizer -> [events_run, rating_sum]}`.
- **Per-user join count**: for telemetry / split logic.

**Follow-formation rule** (runs inside `resolve_event`, after valence is known):
for each ordered pair `(U, V)` who shared a **positive** experience at this event
and where `U` does not already follow `V`, `U` follows `V` with probability
`p_follow = clip(base · extraversion(U) · (0.5 + 0.5·agreeableness(U)), 0, 1)`,
weighted up by the strength of the positive valence. New edges are timestamped at
the event's end time and only affect events that start later.

**Seed network** (`seed_follows`, runs once before the timeline starts):
~10–15% of **all** users are chosen as "socially pre-connected" and each given
1–3 follows, biased toward same-geo / higher-extraversion targets. A small slice
of the **cold** users is deliberately included, so some held-out users enter the
timeline with a tiny social graph but still zero interaction history (the
"invited by a friend" cold-start case). Seed edges are plain `Follow` rows
timestamped at `START_DATE` (i.e. before any event), so they count for every
event under the follow-time gate. No pending/request state — matches the backend
`Follow` schema.

**Valence rule** for a pair sharing an event:
- **Positive** if both members stayed and (rated ≥ 3, or did not rate but did not
  leave).
- **Negative** if either member left, or rated ≤ 1.
- Otherwise neutral (no valence update).

Organizer valence for `U` follows the same rule against U's own rating/leave for
that organiser's event.

**Motivation homophily** (applied at `resolve_event`, all 4 archetypes): for each
member `U`, let `same = #roster members sharing U's motivation_type` (excluding
U). Like-minded company improves the experience:
- **Rating bump** — with probability rising in `same / roster_size`, add a small
  positive increment to U's rating before clipping (competitive thrives among
  competitors, social among social, etc.). It's stochastic ("sometimes"), not
  deterministic.
- **Follow boost** — in the follow-formation step, a positive pair `(U, V)` that
  **shares a motivation_type** gets a higher `p_follow`, and a raised chance the
  edge is **mutual** (both follow each other) rather than one-directional.

This reinforces, but does not replace, the valence-driven follow rule: a positive
shared experience is still the precondition; homophily only amplifies it.

### 5. Frequency as soft propensity

Each user gets a per-user intercept `base_propensity(U)` (replacing the global
`LOGIT_BIAS`) tuned so the user's **expected** total joins over the timeline ≈
their tier midpoint:

| Tier | Old (lo, hi) | Target midpoint |
|---|---|---|
| sparse | (2, 6) | 4 |
| occasional | (12, 22) | 17 |
| regular | (28, 45) | 36 |
| frequent | (70, 120) | 95 |

Calibration: over the **same prefiltered candidate set** used in enrollment
(Section 6), compute each user's **static** logit terms once — `w_act·match`,
`comp_fit`, and the roster-size-independent part of `group_fit` — then solve
`base_propensity(U)` so `Σ sigmoid(static + base + δ) ≈ target` via bisection.
`δ` is a **small constant expected-social offset** (the social/organizer terms
are net-positive on average, so omitting them entirely biases counts upward —
`δ` absorbs the bulk of that drift). Residual social pull still tips marginal
joins, so actual counts vary around the target. **Tiers are no longer exact
counts** — this is intended.

### 6. Candidate prefiltering

For each event, candidates = warm **and cold** users whose activity OR
sport-cluster matches the event and who fall within a generous geo radius. Keeps
evaluation count low. Accepted loss: a user cannot randomly stumble into a
far-off, off-preference event.

**Performance honesty:** today's batch sampling is fully vectorised; this design
replaces it with a multi-pass, per-candidate Bernoulli loop in Python, which is
materially slower. Mitigations: keep candidate pools tight, cap passes (≈2–3),
and vectorise the per-pass logit/probability computation across undecided
candidates (only the join-or-not draw and roster update are sequential). Expect a
slower run than the current generator; if it becomes a bottleneck, vectorising a
whole pass at once is the first optimisation.

### 7. Outputs & splits (unchanged contract)

- Same CSV outputs: `users.csv`, `events.csv`, `follows.csv`,
  `interactions.csv`, `train.csv`, `test.csv`, `train_implicit.csv`,
  `cold_start_users.csv`.
- **`follows.csv` is now a sim output**, written after the timeline completes,
  with columns `follower_id`, `following_id`, `time_created` (matching the
  backend `Follow.time_created` field). The standalone `generate_follows()`
  pre-pass is removed.
- **`events.csv` attendance fields are emergent (B1/B2).** `fill_rate`,
  `participant_count`, `social_density_cat`, and `avg_organizer_rating` are
  computed from the **actual final roster / accumulated ratings** in a finalize
  pass after the timeline, replacing the pre-baked Beta draws in
  `generate_events`. There is one source of truth for who attended.
  (`skill_diversity` stays a pre-baked approximation — it isn't derived from
  roster identities, so the timeline doesn't make it stale.)
- `interactions.csv` gains/keeps: `signal_type`, `rating`, `label`,
  `implicit_label`, `signal_weight`, `timestamp`, plus **new** social/roster
  features (`n_known_in_roster`, `n_unknown_in_roster`, `known_valence`,
  `n_same_motivation`, `acquaintance_target_gap`, `organizer_score`,
  `organizer_first_time`, `join_order`). These are **snapshotted at U's decision
  moment** (the partial roster as U joined), not the final roster. The old
  `organizer_is_followed` column is removed.
- **Zero-join warm users (B3).** After the sweep, any warm user with no rated
  interaction is given one synthesized `join_rated` to their best-matching event,
  so the LOO split's "one test row per warm user" guarantee holds. Count of such
  fallbacks is reported.
- Leave-one-out per warm user and held-out 1000 cold users: unchanged.
- Early-timeline events naturally carry weak social/reputation signal (only the
  seed follows exist) — realistic warm-up, no special handling.

## Components & responsibilities

| Unit | Responsibility | Depends on |
|---|---|---|
| `generate_users` | sample users; uniform Big Five; archetype + freq tier; survey-preference fields from own broad distributions | — |
| `generate_events` | sample events with start_time, organiser, capacity (no pre-baked attendance) | users (organiser ids) |
| `seed_follows` | small pre-timeline seed network (~10–15% of users, incl. some cold) | users |
| `calibrate_propensity` | per-user intercept from static match | users, events |
| `social_state` | co-attendance map + follow set + organiser stats (mutable) | seed_follows |
| `run_enrollment(E)` | one event's one-by-one join process | match, social_state |
| `resolve_event(E)` | ratings/leaves for roster; form follows; emit rows | social_state |
| `finalize_events` | back-fill emergent attendance fields onto `events.csv` | rosters |
| `ensure_min_joins` | synth fallback join for zero-join warm users (B3) | interactions |
| `build_splits` | LOO + cold split | interactions |

`social_state` is the one stateful unit; everything else reads it through a
narrow interface (`social_block(u, roster, t)`, `organizer_rep(u, org)`,
`update_after_event(...)` which also forms new follow edges). The follow network
is initialised from `seed_follows`, then grown by `social_state` over the
timeline, and dumped to `follows.csv` (seed + grown edges) at the end.

## Out of scope (noted, not fixed here)

- **`CLUSTER_EFA` / `CLUSTER_ATTRS` provenance.** These are hand-authored values
  that do **not** match the thesis's actual EFA/HDBSCAN output (different cluster
  taxonomy; clean `[0,1]` values vs. the thesis's z-scored centroids). This
  redesign does not touch them, but for thesis integrity they should later be
  either regenerated from the real pipeline or explicitly disclaimed.

## Testing

- **Determinism**: same `SEED` → identical outputs.
- **Frequency calibration**: per-tier mean join count within ±15% of target
  midpoints over the full run.
- **Social cascade sanity**: events should show join_order correlation between
  followed/known pairs (followed users cluster in roster order more than chance).
- **Valence effect**: holding match constant, users with prior positive history
  toward roster members join at higher rate than those with negative history.
- **Follow seed + growth**: `follows.csv` starts at the seed size (~10–15% of
  users with 1–3 follows each, seed edges timestamped at `START_DATE`) and grows
  monotonically over time; every `time_created` falls within the window; no
  follow edge is referenced by a join decision before its `time_created`.
- **Cold-user seed**: a small, non-zero number of cold users appear as followers
  in the seed; cold users still have zero interaction rows before the timeline.
- **Follow homophily**: extraverted users accumulate more follows on average; new
  (grown) follows correlate with prior positive co-attendance.
- **Emergent event fields**: `participant_count` in `events.csv` equals the
  actual roster size; `avg_organizer_rating` matches ratings accumulated for that
  organiser. No event reports a fill it didn't have.
- **Min-join guarantee (B3)**: every warm user has ≥1 rated interaction, so
  `test.csv` has exactly one row per warm user.
- **Survey-field spread**: the decoupled survey fields show wide, non-degenerate
  distributions across users (not collapsed near a single value).
- **Acquaintance-target effect**: holding match constant, a low-`acquaintance_pref`
  user joins friend-packed events *less* than a high-`acquaintance_pref` user
  (penalty in both directions, not monotonic).
- **New-people effect**: high `enjoys_meeting_new_people` users join
  stranger-heavy events at a higher rate.
- **Group-size fit**: small-group preferrers under-join large-capacity events.
- **Competition fit**: high `motivated_by_competition` users skew toward
  higher-`skill_level` events.
- **Motivation homophily**: same-motivation roster mates correlate with higher
  ratings and more (and more *mutual*) follows than mixed-motivation rosters,
  holding match/valence constant.
- **Split integrity**: every warm user has exactly one test row; no cold user in
  train/test; no leave row used as a LOO positive.
- **Schema**: `interactions.csv` has the new columns and not the removed one.
