# Comparative Implementation Study of a Recommender under Synthetic Cold-start Constraints

University graduate study of Informatics

**Reo Turčinović**

Course: Analiza velikog obujma podataka (Large-Scale Data Analysis)  
Mentors: prof. dr. sc. Sanda Martinčić – Ipšić, dr. sc. Karlo Babić

Rijeka, June 2026

---

## Contents

1. [Introduction](#1-introduction)
2. [Methodology](#2-methodology)
   - 2.1 [System Overview](#21-system-overview)
   - 2.2 [Data model (relevant fields)](#22-data-model-relevant-fields)
     - 2.2.1 [Users](#221-users)
     - 2.2.2 [Sports](#222-sports)
     - 2.2.3 [Events](#223-events)
     - 2.2.4 [Interaction simulation](#224-interaction-simulation)
     - 2.2.5 [Social structure](#225-social-structure)
     - 2.2.6 [Evaluation split](#226-evaluation-split)
   - 2.3 [Features](#23-features)
     - 2.3.1 [Target Variables](#231-target-variables)
   - 2.4 [Models](#24-models)
     - 2.4.1 [Baseline](#241-baseline)
     - 2.4.2 [LightGBM LambdaMART](#242-lightgbm-lambdamart)
     - 2.4.3 [Factorization machines](#243-factorization-machines)
     - 2.4.4 [BPR matrix factorization](#244-bpr-matrix-factorization)
     - 2.4.5 [LightGCN](#245-lightgcn)
     - 2.4.6 [DeepFM](#246-deepfm)
   - 2.5 [Evaluation metrics](#25-evaluation-metrics)
     - 2.5.1 [Weighted NDCG@10](#251-weighted-ndcg10)
     - 2.5.2 [Recall@10](#252-recall10)
     - 2.5.3 [Evaluation slices](#253-evaluation-slices)
     - 2.5.4 [Auxiliary metric](#254-auxiliary-metric)
3. [Results](#3-results)
   - 3.1 [Poor Performance and Pitfalls](#31-poor-performance-and-pitfalls)
   - 3.2 [Results After the Fix](#32-results-after-the-fix)
4. [Application Integration and Live Inference](#4-application-integration-and-live-inference)
   - 4.1 [Offline Training and Live Inference](#41-offline-training-and-live-inference)
   - 4.2 [Architecture](#42-architecture)
   - 4.3 [Feature Bridge](#43-feature-bridge)
   - 4.4 [Updating the Model](#44-updating-the-model)
5. [Conclusion](#5-conclusion)
6. [References](#6-references)
7. [List of Tables](#7-list-of-tables)

[Appendix](#appendix)

---

## 1. Introduction

This paper documents the design, implementation, and evaluation of a multi-tier machine learning recommender system for MoveUs, a fitness-social mobile application built on a Django/GraphQL backend. The recommender replaces the chronological feed with a personalised ranking of upcoming events, grounded in the EFA-based sport-personality framework developed in the author's thesis [1].

---

## 2. Methodology

### 2.1 System Overview

MoveUs is a Django 5.2 application exposing a GraphQL API (Graphene-Django). Users create and join sporting events, follow each other, rate past events (0–4 scale), and receive a personalised feed of upcoming events and social posts.

### 2.2 Data model (relevant fields)

The dataset is produced by a generative simulation that manufactures a population of users, a calendar of events, and the interactions between them. Each observable signal (user joining an event, rating it, leaving early, or following another person) is the outcome of explicit, interpretable mechanisms, so that the regularities in the data correspond to structure that was deliberately modelled rather than to arbitrary noise.

#### 2.2.1 Users

The user dataset is synthetically generated to model a diverse population of plausible participants. A Python simulation produces 10,000 users, each described by demographic, geographic, psychological, motivational and self-reported preference attributes. Personality, motivation and stated preference are generated as independent axes, reflecting that a person's reported wishes are not a deterministic function of their disposition; each preference field is therefore drawn from its own distribution so that it carries genuine variation across the population. The attributes and their generation rules are summarised in Table 1.

**Table 1. User attributes and generation rules**

| Variable | Description |
|---|---|
| Age | Integer, drawn uniformly over 16–64, reflecting a sport-active adult range |
| Gender | Male ≈ 48%, Female ≈ 48%, Non-binary ≈ 2%, Prefer-not-to-say ≈ 2% |
| Location | Latitude/longitude sampled from one of five urban geographic clusters, each modelled as a Gaussian around a centre, producing realistic spatial concentration |
| OCEAN traits (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism) | Each drawn from a Normal(0.5, 0.1) distribution clipped to [0,1], i.e. a shared, mildly varying population distribution |
| Hardiness | Normal distribution, represents mental toughness |
| Confidence, Locus of control | Drawn from a Beta(4, 3) distribution, mildly skewed toward the upper range |
| Motivation archetype | Categorical: competitive (15%), casual-recreational (40%), social (30%), unmotivated (15%). Governs rating tendency, drop-out propensity, attendance frequency and sensitivity to social context |
| Frequency of physical activity | Categorical (sparse / occasional / regular / frequent), drawn conditionally on the motivation archetype; each tier maps to an expected number of attendances over the time window |
| Preferred activities and skill levels | One to four activities selected per user, each tagged with a skill level (0–3) |
| Maximum travel distance | Kilometres the user will travel, spanning roughly 2–50 km |
| Preferred group size | Desired number of participants (me+1–10); influences attendance only for activities without a fixed format (hiking, walking, yoga, ...) |
| Availability | Subset of seven weekdays and four day-parts (morning, afternoon, evening, night) |
| Participation groups | Multi-hot over the social circles a user will mix with: close contacts (friends/family), friends-of-friends, and strangers with common interests |
| Acquaintance preference | Desired number of familiar faces present, from none to everyone |
| Organising, leadership inclination | Willingness to host an event and tendency toward leadership roles |

#### 2.2.2 Sports

Activities are organised into eight sport clusters derived from a factor analysis and clustering of a sport-attribute catalogue (factors of sports used: ball sports, endurance, precision, risk, combat, mind-body, strength, aquatic). Each cluster carries characteristic attributes ([1] from previous work: Table 17: Found correlations between user psychological traits and sport attributes) which determine how well a user's personality aligns with a given activity.

#### 2.2.3 Events

The event dataset comprises 3,333 events distributed across a 24-month window. Each event is characterised by its activity and sport cluster, difficulty, capacity, timing, location and organiser; attendance-derived quantities are not assigned in advance but emerge from the interaction simulation (Table 2).

**Table 2. Event attributes**

| Variable | Description |
|---|---|
| Activity / sport cluster | Activity sampled with realistic (power-law) frequencies; mapped to one of eight clusters |
| Skill level | Integer 0–3 from Beta(1.5, 3), skewed toward beginner-friendly events |
| Max participants | Log-normal centred near eight, clipped to 2–50 |
| Duration | Hours, Normal(1.5, 0.5) clipped to 0.5–4.0 |
| Start and end time | Start on a random day in the window, biased toward evenings (~60%); end follows from the duration |
| Location | From the same five urban clusters as users |
| Organiser | Drawn from the minority of users who report willingness to organise or a tendency toward leadership roles |

Each event has an activity and sport cluster, a skill level, a capacity, a start and end time within the simulation window, a geographic location drawn from a set of urban clusters, and an organiser. Activities are sampled with realistic frequencies, and events are spread across the calendar with day-of-week and time-of-day patterns. Roughly one user in twelve is eligible to host, so organisers are comparatively rare.

#### 2.2.4 Interaction simulation

Interactions are produced by advancing through events in chronological order and simulating attendance participant by participant, so that each decision is conditioned on the roster already formed. Every interaction is recorded as one of three signal types together with the information needed to train and evaluate the recommender (Table 3). Across the population this yields on the order of 300,000 interactions.

**Table 3. Interaction signal fields**

| Variable | Description |
|---|---|
| Signal type | Reaction to the event (attended and left a rating, unrated attendance, or early departure) |
| Rating | 0–4 for rated attendances. Obtained by taking the personality–activity fit as a base, adjusting it for social satisfaction (preferred company and acquaintance count) and like-minded company, and adding archetype-specific noise |
| Signal weight | A single numeric value expressing how informative the signal (rating) is. A positively-rated attendance carries the most weight (3.0), a poorly-rated one less (2.0), a silent attendance least (1.0), and an early departure a negative weight (−1.5) |
| Timestamp | Time of the interaction within the simulation window |
| Social context | Point-in-time counts of known and same-circle attendees present when the user joined |

Interactions are generated by advancing through the events in chronological order and simulating attendance one participant at a time. An event begins with only its organiser; eligible users — those whose interests, location and availability make them plausible candidates, and who are not already committed to an overlapping event — then decide in turn whether to join, each decision conditioned on who is already present. A join becomes more likely when the event matches the user's activity and skill preferences, lies within their travel range, fits their availability and preferred session length, and when the existing roster already contains people the user knows. Because attendees are added one at a time and later candidates can see who has already joined, a popular event accumulates familiar faces as it fills, allowing social clustering to emerge rather than being imposed.

When an event concludes, each attendee produces a signal. The rating reflects the personality–activity fit, raised when the realised company matches the user's preferences and when like-minded participants are present. Positive shared experiences strengthen the social graph: participants who enjoyed an event together may begin to follow one another, and may record an explicit "like" of a co-attendee, with like-minded pairs more likely to form reciprocal ties. Negative experiences and early departures leave a trace that discourages future contact. In this way the network the recommender ultimately learns from is itself a product of the simulated history.

**Scripted Dataset Generation**

The scripted dataset is produced by a fully deterministic Python simulation with a fixed random seed (42). It uses identical population parameters to the LLM dataset — 10,000 users, 3,333 events, a 24-month window — but every behavioural decision is governed by explicit mathematical rules rather than language model generation.

**Join probability model.** The core of the simulation is a logistic scoring function evaluated for each eligible (user, event) pair. A user is first filtered for hard eligibility: they must not already be committed to an overlapping event, the event must fall on a day and time-part they have marked available, the event location must be within their stated maximum travel distance, and the skill level of the event must be compatible with their declared skill in that activity. Eligible users then receive a continuous join score as a weighted sum of soft signals:

| Signal | Weight |
|---|---|
| Activity preference match | 2.0 |
| Skill level alignment | 1.5 |
| Group size compatibility | 0.8 |
| Participation tier match | 0.9 |
| Event duration fit | 0.6 |
| Organiser reputation | 0.4 |
| Social influence (archetype-scaled) | variable |

#### 2.2.5 Social structure

Familiarity between two participants is modelled along two channels: an explicit follow relationship, and a record of having previously attended the same events, weighted by whether those shared occasions went well or badly. A modest set of follow relationships exists from the outset, representing users connected before any activity takes place; further ties form during the simulation, as participants who share a positive experience begin to follow one another, with like-minded pairs more likely to form reciprocal connections. Two preferences further shape attendance: the number of familiar faces a user is comfortable with, so that both an empty room and a crowd of strangers can discourage the appropriate person, and the social circles a user is willing to mix with — close contacts, friends-of-friends, or strangers who share an interest.

#### 2.2.6 Evaluation split

The population is divided into warm users, whose interaction history is available for training, and a held-out set of cold users, who have a profile but no prior interactions and represent newcomers. For warm users, a leave-one-out scheme reserves each person's final rated interaction as a test target and uses the remainder for training; cold users are evaluated on profile information alone. Because the simulation unfolds over time, every feature attached to an interaction is computed from information available at the moment it occurred. Precise amounts can be found in Table 4.

**Table 4. Distribution and amount of synthetic data**

| Data | Count |
|---|---|
| Users (total) | 10,000 |
| — Cold-start users | 1,000 |
| Events | 3,333 |
| Interactions (total) | 300,706 |
| — Joined and rated | 189,126 |
| — Joined, no rating | 88,096 |
| — Leave | 23,484 |
| Train split | 188,558 |
| Validation split | 45,106 |
| Test split | 45,106 |
| Cold-user interactions (excluded from train) | 21,936 |

### 2.3 Features

Before any model is built, the raw interaction records are transformed into numeric representations suitable for learning. Three representations are prepared. A user representation summarises each user's stable profile (demographics, stated preferences, and questionnaire responses) together with a record of their accumulated activity. An event representation describes each event by its activity, sport cluster, difficulty, capacity, timing, and realised attendance. A pairwise representation captures the relationship between a particular user and a particular event — the topical and logistical match between the two, and the social context in which the user encountered the event.

Every quantity attached to an interaction is computed using only information available at the moment that interaction took place. A user's accumulated statistics (how many events they have attended, their average rating, their affinity for each activity and cluster) are therefore taken as they stood before the interaction, never using later events. This prevents information from the future leaking into the data and inflating apparent performance.

Features whose scales differ widely (counts, ratings, and binary fields) are standardised so that no single quantity dominates by magnitude alone.

#### 2.3.1 Target Variables

The recommendation algorithm wants to optimise how a user feels during and more specifically after the sports event (scale 0–4). The output is a ranked list of events.

### 2.4 Models

The recommendation problem in MoveUs is treated as an event-ranking task. For each user, the system must score the set of feasible upcoming events and return them in descending order of expected relevance. Because the platform begins in a cold-start regime but then accumulates attendance, rating and social-link signals over time, no single model family is well suited to every stage. The model set is therefore chosen to cover four distinct requirements: a transparent non-personalised reference point, a strong tabular ranking model, a model that handles sparse feature interactions well in cold start, and collaborative models that can exploit interaction history once it becomes available.

The use of synthetic data justifies the inclusion of one neural model. Since the data-generating process is known and highly structured, a higher-capacity model may be able to recover interaction patterns that simpler models cannot. At the same time, synthetic data also increases the risk that a flexible model will fit idiosyncrasies of the simulator rather than learning relationships that would transfer to a live system. For that reason, the methodology includes one neural model as a serious comparison, but does not allow the benchmark to be dominated by neural architectures alone [2].

#### 2.4.1 Baseline

Two simple reference models are retained.

**Uniform random baseline.** This baseline assigns equal score to all feasible candidate events and serves only as a lower bound. It is not expected to be competitive, but it confirms that the learned models extract genuine signal from the data rather than benefiting from evaluation artefacts.

**Popularity and feasibility baseline.** This model first filters out impossible events using hard constraints such as time overlap, availability, capacity and travel distance. The remaining events are then ranked by a simple popularity-oriented score derived from attendance volume, recency and coarse compatibility. A baseline of this kind is important because event recommendation literature consistently shows that popularity and broad contextual fit remain non-trivial signals and should therefore be explicitly beaten by any learned model [3].

#### 2.4.2 LightGBM LambdaMART

Gradient-boosted ranking trees are well suited to MoveUs because the task is heavily feature-driven. Relevance depends on nonlinear thresholds and interactions such as whether the event lies just inside or outside the user's travel radius, whether the event skill level is slightly above the user's comfort zone, or whether the current attendee composition matches the user's familiarity preferences. Tree-based rankers can learn such decision boundaries directly from the pairwise user-event feature representation without requiring manual cross features or dense latent embeddings.

A LambdaMART-style objective is appropriate because the system output is an ordered top list rather than an independent relevance score for each event. In recommendation settings, LambdaMART and related ranking-tree approaches have been adapted to cold-start problems by learning user and item representations from side information and optimising rank-sensitive objectives such as NDCG [4]. That makes LightGBM a strong practical model for MoveUs, where both user profiles and event attributes are informative from the moment the system launches.

LightGBM is preferred to XGBoost for two reasons. First, it is generally faster to train on large sparse tabular problems, which makes hyperparameter search easier within a limited project budget. Second, the ranking implementation in LightGBM is widely used and straightforward to apply to top-k recommendation settings. The role of this model in the benchmark is to test how far a strong tabular ranker can go using engineered user-event features alone.

#### 2.4.3 Factorization machines

Factorization machines are included as the main cold-start hybrid recommender. Their main advantage is that they model both first-order effects and pairwise feature interactions in sparse feature spaces, allowing them to exploit rich user descriptors, event attributes and contextual variables in one shared representation [5].

This is important because MoveUs contains many combinations of attributes that are individually meaningful but too sparse to estimate directly, such as the interaction between a user's motivation archetype and an event's sport cluster, or the interaction between preferred group size and the roster size already present. A linear model would require such interactions to be specified by hand, whereas a factorization machine learns them through low-dimensional embeddings of the features themselves [5].

Factorization machines are therefore especially appropriate for the early life of the system, when there is enough profile and event metadata to form useful feature vectors but not yet enough user-event history for pure collaborative filtering. The cold-start event literature aligns with this choice, showing that content, organiser, location, time and other side-information signals are central when candidate events are new and interaction history is sparse [3].

#### 2.4.4 BPR matrix factorization

Bayesian Personalized Ranking (BPR-MF) is included as the canonical warm-start collaborative baseline. Bayesian Personalized Ranking was developed for top-N recommendation from implicit feedback and remains one of the clearest reference models for pairwise ranking [6]. In MoveUs, once users accumulate joins, ratings and related behavioural signals, BPR-MF provides a clean measure of how much ranking quality can be obtained from collaborative structure alone. It is not intended as the strongest launch model, since it is weak in profile-only cold start, but it remains an important benchmark for the warm-user setting.

#### 2.4.5 LightGCN

LightGCN is the main modern collaborative model. It simplifies earlier graph recommender architectures by removing transformations and nonlinearities that are unnecessary for collaborative filtering, while retaining higher-order message passing over the interaction graph [7].

This makes it well suited to the later stages of MoveUs. User-event joins define a bipartite interaction graph, and follow links and co-attendance patterns provide additional relational structure. LightGCN can exploit this graph more effectively than ordinary matrix factorisation, while remaining simpler and more stable than heavier graph-neural alternatives.

#### 2.4.6 DeepFM

DeepFM is included as the neural hybrid model. It combines a factorization-machine component for low-order feature interactions with a deep component for higher-order nonlinear interactions, both learned from the same sparse input representation [8].

This makes it an appropriate neural model for MoveUs. The dataset is structured and tabular rather than unstructured, and the recommendation signal lies in interactions between user descriptors, event properties and social-context features. DeepFM is designed for precisely this type of sparse feature space.

The use of synthetic data strengthens the case for including one neural model. Since the simulator generates structured interactions between psychological, behavioural and contextual variables, a more flexible model may recover dependencies that simpler learners miss. At the same time, a neural model is not allowed to dominate the benchmark, because synthetic data may reward architectures that fit simulator-specific regularities too closely. DeepFM is therefore treated as a serious comparison model rather than the default choice.

### 2.5 Evaluation metrics

The recommender is evaluated as a ranking system. The metric set is intentionally small and is chosen to reflect the output of the platform: a short ordered list of future events.

#### 2.5.1 Weighted NDCG@10

Weighted NDCG@10 is the primary evaluation metric. It is chosen for three reasons. First, it is rank-sensitive, so placing the best events near the top of the list matters more than ordering errors far below. Second, it is top-heavy, which matches the fact that only a short leading segment of the event feed is practically visible to the user. Third, it supports graded relevance, which is important because the MoveUs outcome variable is not binary: a highly enjoyed event should contribute more than a weakly positive one [9] [10].

The gain values are derived from the observed post-event outcome, so that stronger positive experiences contribute larger gain in the DCG calculation.

#### 2.5.2 Recall@10

Recall@10 is used as the secondary metric. Where NDCG@10 measures both position and graded usefulness, Recall@10 answers the simpler question of whether relevant events appear anywhere in the top ten. It therefore complements NDCG@10 by providing a more direct measure of retrieval success within the visible portion of the list [10].

#### 2.5.3 Evaluation slices

The main metrics are also reported separately for the key subpopulations present in the simulation: cold users, warm users and new events.

This separation is necessary because aggregate averages can conceal the regimes that matter most in practice. A model may perform well overall while remaining weak for cold users or newly created events, both of which are central to MoveUs [11].

#### 2.5.4 Auxiliary metric

MRR is reported only as an auxiliary measure when the evaluation instance contains one principal held-out target event. It is useful for quantifying how early the first relevant event appears, but it is less informative than NDCG@10 when relevance is graded.

---

## 3. Results

### 3.1 Why the Recommender Was Performing Poorly — and How We Fixed It

When the recommendation models were first run on the synthetic dataset, all of the models scored poorly and nearly identical to the random baseline. The best model achieved an NDCG@10 score of 0.18, while random guessing scored 0.16. In practice, this means the models were providing no useful signal whatsoever.

This raised an immediate question: was this a problem with the models themselves, or with the way we were measuring them?

The fundamental structural property of MoveUs is that every sports event happens exactly once. A football match on Saturday morning is a unique, unrepeatable event. It has one location, one time, one set of participants. Once it's over, it never recurs.

This creates a problem for recommendation systems. Almost all collaborative filtering models (BPR-MF, LightGCN, and similar approaches) work by learning from historical patterns: "user A attended events X, Y, and Z, so they might like event W." But this only works if event W shares some identity with events the model has already seen.

When measured, 100% of the events in the test set had never appeared in training. The models therefore fell back to random guessing.

It was also expected that content-based models (Factorization Machines, LightGBM) would do better, since they rely on event attributes (sport type, location, skill level, time of day) rather than historical interaction patterns.

During training, these models were shown positive examples (events a user attended) alongside negative examples (events they did not attend). The negatives were drawn completely at random from the full pool of 2,500+ events.

The problem: most randomly selected events are obviously unsuitable. They're on the wrong day, too far away, or require a skill level the user doesn't have. The model learned to detect these obvious mismatches rather than learning anything subtle about genuine preference.

At evaluation time, the candidate pool was filtered to only feasible events — ones that matched the user's availability, location, and skill level. The model, which had learned to spot infeasible events, was now presented only with feasible ones. Its learned signal was useless in this context, and performance collapsed toward random.

Compounding everything was a problem with how performance was measured. In the original setup, each user was evaluated over the entire catalogue of 2,500+ events simultaneously. Randomly ranking 2,500 events and getting the right one in the top 10 has a probability of roughly 0.4%. This made the evaluation unrealistic: no real user is deciding between every event in the city for the next two years at once.

Four fixes were implemented:

1. **Time-window evaluation.** Given a specific event a user actually attended, how well does the model rank it against other events happening within ±7 days of that event? This reduces the candidate pool from 2,500+ to roughly 25 events, which is a more realistic representation of what a user actually considers.

2. **Per-target evaluation.** Instead of producing one ranking per user, one ranking per positive interaction was produced. If a user attended three events during the test period, three separate ranking instances were evaluated, allowing for a more granular picture of model performance.

3. **Keying events by activity type.** There are 31 sport activities in the dataset, all of which appear in training. A brand-new football match on Saturday is scored using the model's learned representation of "football as an activity," which it has seen many times. This allowed BPR-MF and LightGCN to transfer knowledge from training to genuinely new events.

4. **Feasible negative sampling.** Training negatives are now drawn from events the user could plausibly attend (right day, right time, within travel distance) but chose not to. This forces the model to learn genuine preference distinctions ("why did this user choose yoga over cycling on a Tuesday evening?") rather than trivial feasibility distinctions.

### 3.2 Results After the Fix

**Table 5. Overall benchmark results (candidate pool ≈ 24.6 events)**

| Model | NDCG@10 | Recall@10 | MRR |
|---|---|---|---|
| Random | 0.3710 | 0.5678 | 0.3539 |
| Popularity | 0.4625 | 0.7008 | 0.4341 |
| LightGBM-LambdaMART | 0.6640 | 0.8345 | 0.6699 |
| Factorization Machine | 0.7095 | 0.8942 | 0.7037 |
| BPR-MF | 0.5497 | 0.8109 | 0.5116 |
| LightGCN | 0.5631 | 0.8287 | 0.5214 |
| **DeepFM** | **0.7417** | **0.9037** | **0.7444** |

After the protocol fix, the models produce a clear and meaningful ordering. DeepFM achieves the highest score across all three metrics. The progression across model families is consistent:

> Random (0.371) → Popularity (0.463) → BPR-MF (0.550) → LightGCN (0.563) → LightGBM (0.664) → FM (0.710) → DeepFM (0.742)

Each tier represents a genuine step over the previous one. The random baseline at 0.371 reflects the time-windowed pool of ~25 events — this is the mathematical floor for uniform ranking at that pool size, and any model above it has extracted real signal from the data.

Popularity (0.463) confirms that activity-level attendance frequency carries useful prior information even before any personalisation. LightGBM (0.664) demonstrates that engineered pairwise features alone capture a substantial portion of the recommendation signal. FM (0.710) improves on LightGBM by learning second-order cross-feature interactions implicitly through embeddings, capturing patterns that tree models represent less efficiently in sparse spaces. DeepFM (0.742) adds a deep MLP component on top of the FM term, recovering higher-order nonlinear dependencies that the structured synthetic data makes accessible.

Recall@10 for DeepFM reaches 0.9037, meaning that in 9 out of 10 evaluation instances the attended event appears in the top 10 of a 25-event candidate pool.

---

**Table 6. Warm user results (candidate pool ≈ 24.5 events)**

| Model | NDCG@10 | Recall@10 | MRR |
|---|---|---|---|
| Random | 0.3723 | 0.5686 | 0.3555 |
| Popularity | 0.4628 | 0.7004 | 0.4352 |
| LightGBM-LambdaMART | 0.6642 | 0.8344 | 0.6707 |
| Factorization Machine | 0.7091 | 0.8932 | 0.7041 |
| BPR-MF | 0.5514 | 0.8124 | 0.5139 |
| LightGCN | 0.5651 | 0.8305 | 0.5239 |
| **DeepFM** | **0.7412** | **0.9029** | **0.7447** |

Warm user results closely mirror the overall numbers, as warm users make up the majority of the test population. Model rankings are identical to the overall slice.

---

**Table 7. Cold user results (candidate pool ≈ 26.3 events)**

| Model | NDCG@10 | Recall@10 | MRR |
|---|---|---|---|
| Random | 0.2935 | 0.5159 | 0.2540 |
| Popularity | 0.4469 | 0.7222 | 0.3711 |
| LightGBM-LambdaMART | 0.6522 | 0.8413 | 0.6226 |
| Factorization Machine | 0.7354 | 0.9524 | 0.6799 |
| BPR-MF | 0.4469 | 0.7222 | 0.3711 |
| LightGCN | 0.4469 | 0.7222 | 0.3711 |
| **DeepFM** | **0.7700** | **0.9524** | **0.7250** |

Two findings stand out in the cold user slice.

**Content models score higher on cold users than on warm users.** FM and DeepFM both improve when moving from warm to cold users (FM: 0.709 → 0.735; DeepFM: 0.741 → 0.770). Cold users have no interaction history; the models score them purely from profile features — sport preferences, availability, location, skill level — which in this synthetic dataset are designed to faithfully encode each user's preferences. Warm users additionally receive interaction-derived features (affinity scores, attendance counts), which introduce noise the profile signal does not carry. This result reflects a property of synthetic data: the profile is a near-perfect summary of preference by construction. On real-world data, where self-reported profiles are noisier, this pattern would likely reverse.

**Collaborative models fall to the popularity floor on cold users.** BPR-MF and LightGCN both score identically to Popularity (0.4469 NDCG@10) for cold users. These models have no learned user embedding for users with no training history and fall back to the activity-popularity score. This is the expected behaviour of collaborative filtering under cold-start conditions and confirms that the fallback mechanism is functioning correctly.

**Table 8. Warm vs cold gap for each model**

| Model | Warm NDCG@10 | Cold NDCG@10 | Cold − Warm |
|---|---|---|---|
| DeepFM | 0.7412 | 0.7700 | +0.029 |
| Factorization Machine | 0.7091 | 0.7354 | +0.026 |
| LightGBM-LambdaMART | 0.6642 | 0.6522 | −0.012 |
| BPR-MF | 0.5514 | 0.4469 | −0.106 |
| LightGCN | 0.5651 | 0.4469 | −0.118 |

LightGBM shows a smaller warm advantage and does not fall back to popularity, because it relies on profile features rather than learned embeddings. The slight warm advantage (0.6642 vs 0.6522) suggests that interaction-derived features provide marginal additional signal for warm users.

**Model selection.** DeepFM is the recommended model for both warm and cold users in this benchmark. For warm users it achieves NDCG@10 = 0.7412 and Recall@10 = 0.9029; for cold users it leads at 0.7700 NDCG@10. BPR-MF and LightGCN are appropriate for studying collaborative signal strength once warm-user history accumulates, but they require a content-based or popularity fallback for cold users at launch.

---

## 4. Application Integration and Live Inference

### 4.1 Offline Training and Live Inference

The synthetic dataset described in Section 2 is used only offline: it is consumed once to fit model parameters, then set aside. At inference time the model receives a different set of inputs — the requesting user's live profile and the set of events currently scheduled in the Django database — and produces a ranked list from those inputs directly. No pre-computed rankings are stored; the model scores each candidate event from scratch on every feed request.

The offline/online split is a standard pattern in production recommendation systems. Training requires a full pass over historical data and is computationally expensive; inference requires only a single forward pass and is fast. Separating the two allows the model to be trained periodically as interaction history accumulates while serving every feed request in real time.

### 4.2 Architecture

Three components form the path from a trained model to a ranked feed response.

`ml/models/run_benchmark.py` runs the full training and evaluation pipeline. After comparing all models on the protocol described in Section 2.5, it identifies the one with the highest overall NDCG@10 — DeepFM in the current benchmark — moves any GPU tensors to CPU so the serialised file is portable across environments, and writes the model to `ml/models_store/best_model.pkl`. The archive includes the fitted `StandardScaler` from the feature context. The scaler is the only training artefact strictly required at inference time: it records the mean and standard deviation computed over the training features and must be reapplied to every new feature vector so that input scales remain consistent with what the model saw during training. A separate metadata file records which model was saved.

`ml/recommender_service.py` exposes `RecommenderService`, a singleton loaded once at Django application startup. Its `score_live(user, events)` method accepts a Django `User` ORM object and a list of Django `Event` objects, builds feature rows from them through the bridge described in Section 4.3, temporarily injects those rows into the in-memory feature context, calls `model.score()`, and returns an array of scores. The injected rows are removed in a `finally` block so the feature context is not permanently modified between requests.

`main/feed/ml_recommender.py` implements the feed interface. On each request `MLFeedRecommender` fetches all scheduled events in a single prefetched query that includes location and activity data, retrieves the requesting user's preferences and availabilities, and passes both to `RecommenderService.score_live()`. Events are returned in descending score order. If the model is not loaded or scoring raises an exception, the feed falls back to chronological ordering.

### 4.3 Feature Bridge

The model's feature context was built from synthetic CSV files with flat column names (`activity_id`, `sport_cluster`, `day_of_week`, `time_of_day`, `duration_hours`, and so on). The live Django schema uses relational models with foreign keys and normalised availability rows. A bridge function translates between the two formats at request time, with no schema changes on either side.

For each event, the bridge reads `activity_id` from the foreign key, looks up the corresponding `sport_cluster` in the static `ACTIVITY_CLUSTER` mapping, derives `day_of_week` from `start_time.weekday()`, assigns `time_of_day` by bucketing the start hour into morning (06:00–11:59), afternoon (12:00–16:59), evening (17:00–21:59), or night, computes `duration_hours` from the difference between start and end time, and reads coordinates from the related `Location` object.

For each user, the bridge reads latitude and longitude from the `User` model, then pulls `max_travel_distance`, `preferred_session_duration`, `preferred_group_size`, and `motivated_by_competition` from `UserPreferences`. Availability days and times are collected from the `UserAvailability` relation and serialised as comma-separated integers, matching the format the feature context's `_raw_pair` method expects. Preferred activity IDs come from `UserPreferredActivity`. When a preference field is null, a sensible default is applied: 10 km travel radius, 60-minute session, group of five.

Since no real application user appeared in the synthetic training set, every live user is treated as cold-start: interaction history fields (activity affinity, join counts, average rating, no-show rate) default to zero and the model scores each user on their profile features alone. This is consistent with how cold users were handled during evaluation and means that the profile bridge is the primary source of personalisation signal for all live users.

### 4.4 Updating the Model

A management command wraps the retrain workflow:

```
python manage.py retrain --data-dir ml/data --results-dir ml/results/llm
```

This reruns the full benchmark on the specified dataset, serialises the new best model, and resets the `RecommenderService` singleton so the next feed request loads the updated model without a server restart. The command accepts an arbitrary data directory, so it can be pointed at exported real interaction logs once sufficient volume has accumulated, allowing the synthetic training data to be replaced with observed behaviour over time.

---

## 5. Conclusion

This seminar paper presented the methodological design of a recommender-system benchmark for MoveUs, a fitness-social application centred on personalised ranking of upcoming events. The study defined a synthetic but structured dataset, specified the feature representations used for event ranking, selected an appropriate set of recommendation models, and established a ranking-based evaluation framework.

The proposed benchmark combines non-personalised baselines, a modern tabular ranker, hybrid feature-based recommenders, collaborative filtering models, and one neural model. This design reflects the dual nature of the MoveUs task: profile-based cold start at system launch and interaction-driven recommendation as behavioural history accumulates.

The initial evaluation protocol produced near-random results for all models due to the one-shot nature of sports events: 100% of test events had zero overlap with training events under a temporal split. A redesigned protocol — time-windowed candidate pools, per-target evaluation instances, activity-level item re-keying, and feasible negative sampling — restored meaningful differentiation across model tiers. After the fix, DeepFM achieves NDCG@10 = 0.7417 overall, approximately twice the random baseline of 0.3710, with Recall@10 = 0.9037.

The evaluation framework is centred on Weighted NDCG@10 and Recall@10, with additional reporting for cold users, warm users, and new events. This allows model comparison to remain aligned with the practical structure of the application rather than with a purely generic recommendation setting.

---

## 6. References

[1] R. Turčinović, "Recommendation of Sports Activities Using Synthetic Data Generation Methods and Machine Learning," Rijeka, 2025.

[2] V. W. B. A. D. N. T. D. J. D. & P. C. Anelli, "Top-N recommendation algorithms: A quest for the state-of-the-art," Proceedings of the 30th ACM Conference on User Modeling, Adaptation and Personalization, pp. 121–131, 2022.

[3] A. Q. Macedo, L. B. Marinho and R. L. Santos, "Context-aware event recommendation in event-based social networks," Proceedings of the 9th ACM Conference on Recommender Systems, pp. 123–130, 2015.

[4] P. Nguyen, J. Wang and A. Kalousis, "Factorizing LambdaMART for cold start recommendations," Machine Learning, vol. 104, pp. 223–242, 2016.

[5] S. Rendle, Z. Gantner, C. Freudenthaler and L. Schmidt-Thieme, "Fast context-aware recommendations with factorization machines," Proceedings of the 34th International ACM SIGIR Conference on Research and Development in Information Retrieval, pp. 435–444, 2011.

[6] S. Rendle, C. Freudenthaler, Z. Gantner and L. Schmidt-Thieme, "BPR: Bayesian Personalized Ranking from Implicit Feedback," arXiv, 2012.

[7] X. He, K. Deng, X. Wang, Y. Li, Y. Zhang and M. Wang, "LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation," Proceedings of the 43rd International ACM SIGIR Conference on Research and Development in Information Retrieval, pp. 639–648, 2020.

[8] H. Guo, R. Tang, Y. Ye, Z. Li and X. He, "DeepFM: A Factorization-Machine based Neural Network for CTR Prediction," Proceedings of the 26th International Joint Conference on Artificial Intelligence, pp. 1725–1731, 2017.

[9] Y.-M. Tamm, R. Damdinov and A. Vasilev, "Quality Metrics in Recommender Systems: Do We Calculate Metrics Consistently?," Proceedings of the 15th ACM Conference on Recommender Systems, pp. 708–713, 2021.

[10] W. X. Zhao, Z. Lin, Z. Feng, P. Wang and J.-R. Wen, "A Revisiting Study of Appropriate Offline Evaluation for Top-N Recommendation Algorithms," ACM Transactions on Information Systems, 2022.

[11] D. Lee and P. Brusilovsky, "Alleviating the new user problem in collaborative filtering by exploiting personality information," User Modeling and User-Adapted Interaction, vol. 26, no. 2, pp. 221–255, 2016.

---

## 7. List of Tables

- Table 1: User attributes and generation rules
- Table 2: Event attributes
- Table 3: Interaction signal fields
- Table 4: Distribution and amount of synthetic data
- Table 5: Overall benchmark results
- Table 6: Warm user benchmark results
- Table 7: Cold user benchmark results
- Table 8: Warm vs cold gap for each model

---

## Appendix

### A. Prompt for getting an overview of models and metrics

The full generative prompt used to find relevant research on models and metrics in recommendation systems is provided below for reproducibility and methodological transparency.

> Find academic papers relevant to building an AI-based recommendation app that matches people to physical-activity events in a way that reduces loneliness and increases engagement in sports and other physical or recreational activities. The matching should account for a user's psychological profile and personality (for example OCEAN/Big Five), physical capabilities, sport or activity preferences, compatibility with other people in an event, and team or group dynamics. Include work on AI or machine-learning recommenders, matching algorithms, and related computational approaches for matching a person to an event, another person, an existing team or group, or a newly formed group depending on the activity and who is available. Also include relevant behavioral research on what actually reduces loneliness and helps people stay engaged in physical activity in app-based social matching contexts.
>
> Find academic papers relevant to choosing and comparing machine-learning models for a social sports app that must rank events for each user and return an ordered top list of events. The project should prioritize models that are realistic to compare within one student project or thesis rather than only the hardest state-of-the-art systems. The app has profile features for users (even personality descriptors) and structured features for events, and then accumulates interaction signals over time such as joins, ratings, early departures, and social links. The search should cover practical model families for event ranking and top-N recommendation in this kind of setting, including models suitable for profile-only cold start and models that improve as user-event interaction history grows.
>
> Also find academic papers on the best evaluation methods for this task. The focus is on evaluation for ordered event recommendation and top-k ranking, including leave-one-out or similar protocols, ranking metrics, and how to evaluate both overall ranking quality and cold-start users separately. The goal is to identify which models are strongest and most defensible for this problem, and which evaluation setup and metrics are most appropriate for comparing them fairly.

### B. Prompt for Coding

In coding, data generation, benchmark and model specification, Claude Opus 4.8 was used.

> Analyze the submitted .py file and results. Is it the data, methods or metrics that are giving low results. What could the reasons be? Explain and suggest improvements.

> Summarize the conversation here into concrete and actionable steps, like you would a technical documentation. Be concise and precise. Do not overcomplicate with complex terminology, but do not leave anything out. Do not paraphrase or repeat the same point.
