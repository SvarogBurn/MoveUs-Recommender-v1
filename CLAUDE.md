# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

**Docker (recommended):**
```bash
docker compose up -d --build       # start web + worker + redis
docker compose logs -f web         # tail logs
docker compose run --rm web python manage.py migrate
docker compose up -d --build web   # rebuild after code changes
```

**Without Docker** (requires Redis on :6379 and PostgreSQL):
```bash
pip install -r requirements.txt
python manage.py runserver         # or: daphne -b 0.0.0.0 -p 8000 core.asgi:application
celery -A core worker -l info      # separate terminal
```

GraphQL playground available at `http://localhost:8000/graphql` when `DEBUG=True`.

## Tests

Tests live in `ml/tests/` only (ML pipeline unit tests). Django app has no test suite.

```bash
pytest                             # run all ml tests
pytest ml/tests/test_deepfm.py    # run a single file
pytest -k "test_candidates"       # run by name pattern
```

`CELERY_TASK_ALWAYS_EAGER=True` in `.env` makes Celery tasks run inline during development.

## ML pipeline (standalone, no Django)

The full training pipeline runs independently of Django:

```bash
python -m ml.gen.timeline          # generate synthetic data → ml/data/
python -m ml.models.run_benchmark  # train all models, saves best to ml/models_store/best_model.pkl
```

`ml/data/` and `ml/results/` are gitignored. `ml/models_store/best_model.pkl` and `best_model_metadata.txt` **are** tracked.

## Architecture

### Django app

Single installed app `main` re-exports all models from sub-packages (`main/models.py`). Domain lives in `main/{user,event,social,chat,feed,activity,location,notification,search}/`.

### GraphQL

`api/schema.py` defines the schema. `api/graphql/query.py` and `mutation.py` **auto-discover** all `*Query` and `Mutation` classes by scanning `api/graphql/*/queries.py` and `mutations.py` — adding a new query file is enough, no manual registration needed.

**Auth**: `CustomGraphQLView` (in `core/urls.py`) extracts a session token from the `Authorization` header (`Bearer <token>`, `Session <token>`, or bare token). There is no JWT middleware. Use the `@require_auth` decorator on resolvers; raise `MUError(MUErrorCode.X)` for domain errors — the view formats these into `extensions.code` in the error response.

**WebSockets**: subscriptions run over Django Channels (Daphne ASGI), defined in `api/graphql/subscription.py` and routed in `core/routing.py`.

### Feed recommender

Pluggable via `settings.FEED_RECOMMENDER` (dot-path to a `FeedRecommender` subclass). Currently `main.feed.ml_recommender.MLFeedRecommender`, which loads `ml/models_store/best_model.pkl` (DeepFM, NDCG@10=0.7231) at startup and scores live events via `ml/recommender_service.py`. Falls back to chronological order on any error.

To swap the recommender, change `FEED_RECOMMENDER` in `core/settings.py`.

### ML pipeline structure

| Path | Role |
|---|---|
| `ml/gen/timeline.py` | Top-level generator — calls users, events, enrollment, calibrate in order |
| `ml/gen/config.py` | All generator constants (N_USERS, N_EVENTS, seeds, geo clusters, etc.) |
| `ml/features.py` | Builds 15-dim pairwise feature vectors + StandardScaler from CSVs |
| `ml/models/context.py` | `FeatureContext` and `ACTIVITY_CLUSTER` mapping (activity_id 0–30 → cluster 0–7) |
| `ml/models/run_benchmark.py` | Trains all registered models, evaluates, serialises the winner |
| `ml/eval/harness.py` | Time-windowed per-target evaluation protocol |
| `ml/recommender_service.py` | Django-facing bridge: `score_live(user, events)` builds ORM→feature vector |

**Feature dimensions**: pairwise vector is 15-dim (activity match, distance score, availability, duration gap, group size gap, skill level, competition motivation, 4 history scalars, 4 affinity scalars, event popularity). All live users are cold-start (history = 0).

**ActivityKind enum** (0–30 in `shared/enums.py`) maps directly to `ACTIVITY_CLUSTER` keys — Django `Event.activity_id` and synthetic `activity_id` are the same space.

### Key settings

| Setting | Value / purpose |
|---|---|
| `FEED_RECOMMENDER` | Dot-path to active `FeedRecommender` class |
| `GRAPHQL_MAX_QUERY_DEPTH` | 10 — enforced by `depth_limit_validator` |
| `MAX_PAGE_SIZE` | 100 — enforced by `validate_pagination` in `shared/utils/pagination.py` |
| `STORAGE_BACKEND` | `gcs` (Google Cloud Storage) for attachments |
| `CELERY_TASK_ALWAYS_EAGER` | Set `True` in `.env` for local development |
