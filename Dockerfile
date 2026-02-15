FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY . /app/

RUN apt-get update && apt-get install -y

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=8000
EXPOSE ${PORT}

CMD daphne -b 0.0.0.0 -p ${PORT} core.asgi:application
