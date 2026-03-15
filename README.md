# Running the Project Locally

This guide explains how to run the backend locally either **directly
using Python** or **inside a Docker container**.

## Prerequisites

Before starting, ensure the following:

- You have a copy of the `.env` file placed in the **project root directory**
- A **Redis instance** is running on port `6379`

You can start Redis using Docker:

```bash
docker run -d -p 6379:6379 redis
```

Or run it locally if Redis is installed:

```bash
redis-server
```

## Option 1 - Run Directly with Python

### 1. Create a virtual environment

```bash
python -m venv venv
```

### 2. Activate the virtual environment

**macOS / Linux**

```bash
source venv/bin/activate
```

**Windows**

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the development server

```bash
python manage.py runserver
```
If you encounter problems with Django's built-in development server, you can also try running it using `daphne`:

```bash
daphne -b 0.0.0.0 -p 8000 core.asgi:application
```

The server will be available at:

```
http://localhost:8000
```

## Option 2 - Run with Docker

### 1. Build the Docker image

```bash
docker build -t moveus:latest .
```

### 2. Run the container

```bash
docker run -p 8000:8000 --env-file .env moveus
```

The server will be available at:

```
http://localhost:8000
```
