from dataclasses import dataclass

from django.core.cache import caches
from django.db import connections


@dataclass(frozen=True)
class HealthStatus:
    status: str
    database: str
    cache: str


def get_liveness_status() -> HealthStatus:
    return HealthStatus(status="ok", database="unchecked", cache="unchecked")


def get_readiness_status() -> HealthStatus:
    database_status = "ok"
    cache_status = "ok"

    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        database_status = "error"

    try:
        cache = caches["default"]
        cache.set("healthcheck", "ok", timeout=5)
        if cache.get("healthcheck") != "ok":
            cache_status = "error"
    except Exception:
        cache_status = "error"

    status = "ok" if database_status == "ok" and cache_status == "ok" else "degraded"
    return HealthStatus(status=status, database=database_status, cache=cache_status)
