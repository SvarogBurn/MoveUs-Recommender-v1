# Running the Project Locally

This guide explains how to run the backend locally. The recommended path is **Docker Compose**, which spins up the web server, Celery worker, and Redis as one stack. If you'd rather run Python directly on your machine, see the fallback section at the bottom.

> [!NOTE]  
> The Docker Compose file is also used during production as of this moment, because MoveUs **does not have enough funding** to support a more scalable infrastructure. This is not an ideal solution, but works for now.

## Prerequisites

- A copy of the `.env` file placed in the **project root directory**.
- Docker and the Docker Compose plugin installed (`docker compose version` to verify).

## Option 1 - Run with Docker Compose (recommended)

### Build and start the stack

From the project root:

```bash
docker compose up -d --build
```

This builds the image once and starts three services:

- `web` - Daphne serving the Django app on port `8000`.
- `worker` - the Celery worker that processes scheduled jobs (event phase transitions, event-start notifications).
- `redis` - Redis 7 with AOF persistence, used as both the Channels backplane and the Celery broker.

The server will be available at:

```
http://localhost:8000
```

### Useful commands

```bash
# Tail logs from every service
docker compose logs -f

# Tail logs from just one service
docker compose logs -f web

# Run a one-off Django management command
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py shell

# Restart a service after a code change (rebuild + recreate)
docker compose up -d --build web worker

# Stop everything (data volume preserved)
docker compose down

# Stop and wipe Redis data too
docker compose down -v
```

### Notes on configuration

- `.env` is read by both the `web` and `worker` services. The compose file overrides `REDIS_HOST` to `redis` so the containers reach Redis by service name regardless of what `.env` says.
- Code is baked into the image at build time. After editing source files, run `docker compose up -d --build` to rebuild and restart.

## Option 2 - Run Directly with Python

Use this if you prefer to develop without Docker. You'll need Python 3.11+ and a running Redis instance on port `6379`.

### 1. Start Redis

```bash
docker run -d -p 6379:6379 redis
```

Or, if Redis is installed locally:
```bash
redis-server
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate          # macOS / Linux
venv\Scripts\activate             # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the development server

```bash
python manage.py runserver
```

If you encounter problems with Django's built-in development server, run it via Daphne:

```bash
daphne -b 0.0.0.0 -p 8000 core.asgi:application
```

The server will be available at:

```
http://localhost:8000
```

### 5. Run the Celery worker

In a separate terminal (with the venv activated):

```bash
celery -A core worker -l info
```

The worker uses the same Redis instance as the channel layer (broker on DB `1`, results on DB `2` by default). Override with `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` in `.env` if needed. For tests, set `CELERY_TASK_ALWAYS_EAGER=True` so tasks run inline.
