#!/bin/sh
# Production start: bring the schema up to date as bharosa_owner, then serve.
# A deploy therefore never runs code against an older schema.
#
# Forwarded headers are trusted because the API is only reached through the
# host's proxy, so the rate limiters key on the visitor's address rather than
# the proxy's.
set -e

alembic upgrade head
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips='*'
