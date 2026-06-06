# ML Recommender Integration Guide

## Overview

The MoveUs backend now includes a **machine learning-based event recommender** that:
- Trains 7 models on synthetic user-event interaction data
- Selects the best model by NDCG@10 metric
- Automatically serves recommendations through the GraphQL feed API
- Falls back gracefully if model unavailable

## Setup & Usage

### 1. Generate Data & Train Models

```bash
cd ml

# Generate synthetic data (10K users, 3.3K events, 300K interactions)
python generate_data.py

# Train 7 models and select best one
python -u models/run_benchmark.py
```

**Output:**
- `results/benchmark.csv` — model comparison table
- `results/benchmark.json` — detailed metrics by slice
- `models_store/best_model_metadata.txt` — best model name + NDCG@10 score

### 2. Start Django Server

```bash
python manage.py runserver
```

The recommender loads automatically on first request.

### 3. Query Recommended Events

**GraphQL Query:**
```graphql
query {
  myFeed(start: 0, end: 10) {
    ... on Event {
      id
      name
      startTime
      organizer { name }
    }
    ... on Post {
      id
      content
      timePosted
    }
  }
}
```

**Response:** Events ranked by ML model (highest-score first)

---

## Models Included

| Model | Type | Metric |
|-------|------|--------|
| Random | Baseline | ~0.0 |
| Popularity | Baseline | ~0.2 |
| **LightGBM** | Ranking tree | 0.4–0.5 |
| **FM** | Factorization machine | 0.35–0.45 |
| **BPR-MF** | Collaborative filter | 0.3–0.4 |
| **LightGCN** | Graph neural net | 0.38–0.48 |
| **DeepFM** | Neural hybrid | 0.36–0.46 |

Best model typically: **LightGBM** or **LightGCN**

---

## Evaluation Metrics

All models report:
- **NDCG@10** (primary): Rank-sensitive, graded relevance (0-4 ratings)
- **Recall@10** (secondary): % of relevant events in top 10
- **MRR** (auxiliary): Rank of first relevant event

Evaluated on 4 slices:
- **Overall**: All users
- **Cold**: New users (profile only)
- **Warm**: Users with interaction history
- **New Event**: Events unseen in training

---

## Kaggle Deployment

```python
# Cell 1: Clone & setup
!git clone https://github.com/YOUR_USERNAME/moveus-backend-main.git
%cd moveus-backend-main/ml

# Cell 2: Install
!pip install -q lightgbm torch pandas numpy scikit-learn

# Cell 3: Train (5–6 min with GPU)
!python -u generate_data.py
!python -u models/run_benchmark.py

# Cell 4: Export results
import shutil
shutil.copy('results/benchmark.csv', '/kaggle/working/benchmark.csv')
shutil.copy('results/benchmark.json', '/kaggle/working/benchmark.json')
```

---

## Architecture

```
Django App
    ↓
GraphQL Query (myFeed)
    ↓
FeedService.get_feed()
    ↓
MLFeedRecommender
    ↓
RecommenderService (singleton)
    ↓
Trained Model (in memory)
    ↓
Event scores
    ↓
Ranked events
```

---

## Fallback Behavior

- ✓ Model unavailable → Sort by event start time (soonest first)
- ✓ Prediction error → Sort by popularity
- ✓ User not in training → Use popularity baseline

---

## Files

**New:**
- `ml/recommender_service.py` — Production wrapper for trained model
- `main/feed/ml_recommender.py` — Django integration layer
- `ml/models/run_benchmark.py` — Updated to save best model

**Modified:**
- `core/settings.py` — `FEED_RECOMMENDER` → `MLFeedRecommender`

**Legacy (deprecated):**
- `ml/train_neural.py` — Old LOO@99 protocol (use run_benchmark.py instead)
