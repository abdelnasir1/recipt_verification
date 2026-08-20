#!/bin/sh
set -eu

redis-server \
  --bind 127.0.0.1 \
  --port 6379 \
  --protected-mode yes \
  --daemonize yes \
  --pidfile /tmp/redis.pid \
  --dir /tmp \
  --dbfilename receipt-queue.rdb \
  --save "" \
  --appendonly no

celery -A app.tasks worker \
  --loglevel=info \
  --pool=solo \
  --concurrency=1 \
  --prefetch-multiplier=1 &
worker_pid=$!

cleanup() {
  kill "$worker_pid" 2>/dev/null || true
  redis-cli -h 127.0.0.1 shutdown nosave 2>/dev/null || true
}
trap cleanup INT TERM EXIT

exec uvicorn app.main:app --host 0.0.0.0 --port 8000