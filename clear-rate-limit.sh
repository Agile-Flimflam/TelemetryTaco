#!/bin/bash

# Clear Redis rate limit cache
# This helps when rate limits are changed and old limits are cached

echo "🧹 Clearing Redis rate limit cache..."

# Clear Redis DB 1 (used for cache/rate limiting)
docker-compose exec -T redis redis-cli -n 1 FLUSHDB 2>/dev/null || \
redis-cli -n 1 FLUSHDB 2>/dev/null || \
echo "⚠️  Could not clear Redis cache. Make sure Redis is running."

echo "✅ Rate limit cache cleared (if Redis was accessible)"
