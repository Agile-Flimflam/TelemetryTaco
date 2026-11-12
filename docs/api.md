# API

Every endpoint lives under `/api`. The running backend serves the full OpenAPI schema at `/api/openapi.json` and interactive docs at `/api/docs`. The same schema is committed as `frontend/openapi.json`, and the dashboard's TypeScript types are generated from it.

There is no authentication yet (#30): every endpoint is public.

## Errors and limits

| Status | When |
|---|---|
| 400 | A request the API refuses as a whole: an empty or oversized batch (over `MAX_CAPTURE_BATCH_SIZE`, default 500), a `limit` or `lookback_minutes` below 1, or a malformed `before` cursor. The body is `{"detail": "..."}`. |
| 422 | A payload that fails validation, with Ninja's description of each problem. In a batch, one invalid event rejects the whole request. |
| 429 | A client over its rate limit. The body is `{"detail": "..."}`, and `Retry-After` gives the seconds until the limit resets. |
| 503 | `/api/health/ready` when Postgres or Redis is unreachable. |

Rate limits are per client IP and set per endpoint group: `RATE_LIMIT_CAPTURE_EVENT` for both capture endpoints, `RATE_LIMIT_LIST_EVENTS` for `/api/events`, and `RATE_LIMIT_GET_INSIGHTS` for `/api/insights` and `/api/stats`. See [deployment.md](deployment.md#configuration) for the defaults and for running behind a proxy.

List endpoints are bounded: `limit` is capped at `MAX_EVENTS_LIMIT` (default 200) and `lookback_minutes` at `MAX_INSIGHTS_LOOKBACK_MINUTES` (default 1440).

## `POST /api/capture`

```json
{
  "distinct_id": "user-123",
  "event_name": "page_view",
  "properties": {
    "path": "/"
  },
  "event_uuid": "optional-uuid",
  "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
  "sent_at": "YYYY-MM-DDTHH:MM:SSZ"
}
```

`timestamp` is when the event happened and `sent_at` is when the request left the client, both optional. With both, the server corrects for a wrong client clock by keeping the gap between them and anchoring it to the time it received the request. With only `timestamp`, it's stored as is. With only `sent_at`, it's used as the event time, as before `timestamp` existed. With neither, the server's receive time is used. An event time more than a minute in the future is replaced with the receive time.

`distinct_id` and `event_name` must be 1 to 255 characters. `properties` may be at most `MAX_EVENT_PROPERTIES_BYTES` once serialized as JSON. No string may contain a NUL character. Anything else is rejected with HTTP 422, and in a batch one invalid event rejects the whole request, so nothing is accepted and then lost later.

Response:

```json
{
  "status": "ok"
}
```

## `POST /api/capture/batch`

```json
{
  "events": [
    {
      "distinct_id": "user-123",
      "event_name": "page_view"
    }
  ]
}
```

The response's `accepted` is the number of distinct `event_uuid`s in the request. An event whose `event_uuid` was already stored is accepted but not stored again.

## `GET /api/events?limit=100&before=YYYY-MM-DDTHH:MM:SSZ,EVENT_ID`

Returns recent events ordered by `timestamp desc, id desc`.
For stable pagination, set `before` to the last event's `timestamp,id` pair.
Plain ISO 8601 timestamps are still accepted for backward compatibility.

## `GET /api/insights?lookback_minutes=60`

Returns one point per minute for the last `lookback_minutes` minutes, oldest first, ending with the current minute. Minutes without events have a count of 0, so the series always has `lookback_minutes` points (capped at `MAX_INSIGHTS_LOOKBACK_MINUTES`).

```json
[
  { "bucket": "2026-10-04T18:04:00Z", "time": "18:04", "count": 4 }
]
```

`bucket` is the start of the minute in UTC; format it in the viewer's time zone. `time` is the same minute as `HH:MM` in UTC and is deprecated, kept for older clients.

## `GET /api/stats`

Returns a summary of the last 24 hours plus when the most recent event arrived:

```json
{
  "events_last_24h": 2999,
  "unique_distinct_ids_last_24h": 75,
  "last_event_received_at": "2026-10-04T07:42:00.310Z"
}
```

## `GET /api/health/live` and `GET /api/health/ready`

`live` answers 200 whenever the process is up, without touching its dependencies, so use it for liveness probes. `ready` also checks Postgres and Redis and answers 503 when either fails:

```json
{ "status": "degraded", "database": "error", "cache": "ok" }
```

## Compatibility

The SDK and deployed clients call the capture endpoints, so changes to the API are additive: new fields are optional, and existing fields aren't renamed or removed. Deprecated fields, such as the `time` field on insight points, stay until a major version.
