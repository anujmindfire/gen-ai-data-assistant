#!/usr/bin/env bash
set -e

HOST="${POSTGRES_HOST:-postgres}"
PORT="${POSTGRES_PORT:-5432}"
QDRANT_H="${QDRANT_HOST:-qdrant}"
QDRANT_P="${QDRANT_PORT:-6333}"

echo "Waiting for PostgreSQL at $HOST:$PORT..."
until nc -z -v -w30 "$HOST" "$PORT" 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping..."
  sleep 2
done
echo "PostgreSQL is UP!"

echo "Waiting for Qdrant at $QDRANT_H:$QDRANT_P..."
until nc -z -v -w30 "$QDRANT_H" "$QDRANT_P" 2>/dev/null; do
  echo "Qdrant is unavailable - sleeping..."
  sleep 2
done
echo "Qdrant is UP!"

exec "$@"
