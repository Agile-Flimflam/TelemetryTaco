"""Generate believable product traffic for screenshots and the README demo.

Sends events through the Python SDK, so they take the real ingestion path. It backfills the
last 24 hours (with a busier, wavier final hour so the insights chart has shape), then keeps
streaming live events until stopped.

    PYTHONPATH=sdk python docs/demo/demo_traffic.py --base-url http://localhost:8000

The default rate limit is 1000 captures an hour per IP, so raise RATE_LIMIT_CAPTURE_EVENT
on the backend before running it.
"""

import argparse
import math
import random
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from telemetry_taco import TelemetryTaco

PAGES = [
    "/",
    "/pricing",
    "/docs/quickstart",
    "/docs/sdk/python",
    "/blog/self-hosted-analytics",
    "/dashboard",
    "/settings/billing",
    "/checkout",
]
BUTTONS = [
    ("cta-start-trial", "Start free trial"),
    ("nav-docs", "Docs"),
    ("copy-snippet", "Copy snippet"),
    ("upgrade-plan", "Upgrade to Pro"),
    ("invite-teammate", "Invite teammate"),
]
FEATURES = ["insights_refresh", "event_filter", "csv_export", "dark_mode", "api_keys"]
PLANS = [("starter", 19.0), ("pro", 49.0), ("team", 149.0)]
COUNTRIES = ["US", "GB", "DE", "CA", "BR", "IN", "JP", "AU", "FR", "NL"]
BROWSERS = ["Chrome", "Safari", "Firefox", "Edge"]
ERRORS = [
    ("TypeError", "Cannot read properties of undefined (reading 'map')"),
    ("NetworkError", "Failed to fetch /api/insights"),
    ("ValidationError", "email must be a valid address"),
]

EVENT_WEIGHTS = {
    "page_view": 52,
    "button_click": 22,
    "feature_used": 12,
    "signup_completed": 5,
    "checkout_completed": 4,
    "error": 2,
    "session_started": 3,
}

USERS = [f"user_{n:04d}" for n in random.Random(7).sample(range(1000, 9999), 240)]


def make_event(rng: random.Random) -> tuple[str, str, dict[str, Any]]:
    name = rng.choices(list(EVENT_WEIGHTS), weights=list(EVENT_WEIGHTS.values()))[0]
    user = rng.choice(USERS)
    common = {"$browser": rng.choice(BROWSERS), "$country": rng.choice(COUNTRIES)}
    props: dict[str, Any]
    if name == "page_view":
        props = {"path": rng.choice(PAGES), "referrer": rng.choice(["google", "github", None])}
    elif name == "button_click":
        button_id, text = rng.choice(BUTTONS)
        props = {"button_id": button_id, "text": text, "path": rng.choice(PAGES)}
    elif name == "feature_used":
        props = {"feature": rng.choice(FEATURES), "duration_ms": rng.randint(40, 2400)}
    elif name == "signup_completed":
        props = {"method": rng.choice(["email", "github", "google"])}
    elif name == "checkout_completed":
        plan, price = rng.choice(PLANS)
        props = {"plan": plan, "amount": price, "currency": "USD"}
    elif name == "error":
        error_type, message = rng.choice(ERRORS)
        props = {"type": error_type, "message": message, "path": rng.choice(PAGES)}
    else:
        props = {"entry_path": rng.choice(PAGES)}
    return user, name, {**props, **common}


def events_per_minute(minutes_ago: float) -> float:
    """Daily cycle plus, in the last hour, two waves and a launch-style spike."""
    daily = 14 + 8 * math.sin((24 * 60 - minutes_ago) / (24 * 60) * 2 * math.pi)
    if minutes_ago > 60:
        return daily
    waves = 6 * math.sin(minutes_ago / 9) + 4 * math.sin(minutes_ago / 3.5)
    spike = 22 * math.exp(-(((minutes_ago - 18) / 3) ** 2))
    return max(4.0, daily + 8 + waves + spike)


def backfill(client: TelemetryTaco, rng: random.Random, now: datetime) -> int:
    sent = 0
    for minutes_ago in range(24 * 60, 0, -1):
        count = max(0, round(rng.gauss(events_per_minute(minutes_ago), 2)))
        start = now - timedelta(minutes=minutes_ago)
        for _ in range(count):
            user, name, props = make_event(rng)
            offset = timedelta(seconds=rng.uniform(0, 60))
            client.capture(user, name, props, timestamp=start + offset)
        sent += count
    return sent


def stream(client: TelemetryTaco, rng: random.Random, per_second: float) -> None:
    while True:
        user, name, props = make_event(rng)
        client.capture(user, name, props)
        time.sleep(rng.expovariate(per_second))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--no-backfill", action="store_true", help="Only stream live events")
    parser.add_argument("--no-stream", action="store_true", help="Only backfill, then exit")
    parser.add_argument("--rate", type=float, default=0.5, help="Live events per second")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    with TelemetryTaco(
        args.base_url, batch_size=500, max_queue_size=5000, queue_full_policy="block"
    ) as client:
        if not args.no_backfill:
            sent = backfill(client, rng, datetime.now(UTC))
            client.flush(timeout=120)
            print(f"Backfilled {sent} events over the last 24 hours.")
        if not args.no_stream:
            print(f"Streaming about {args.rate} events a second. Ctrl-C stops.")
            try:
                stream(client, rng, args.rate)
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
