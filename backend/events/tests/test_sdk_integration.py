import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from events.models import Event

# The SDK isn't a backend dependency, so import it straight from the checkout. That keeps this
# test on the SDK code in the same commit, which is the point of it.
SDK_DIR = Path(__file__).resolve().parents[3] / "sdk"
if SDK_DIR.is_dir() and str(SDK_DIR) not in sys.path:
    sys.path.insert(0, str(SDK_DIR))

telemetry_taco = pytest.importorskip("telemetry_taco", reason="needs the repo's sdk/ directory")


@pytest.mark.django_db(transaction=True)
def test_sdk_events_land_in_the_database(live_server):
    happened_at = datetime.now(UTC) - timedelta(minutes=5)

    with telemetry_taco.TelemetryTaco(live_server.url, batch_size=2, flush_interval=0.05) as client:
        client.capture("user-1", "signup", {"plan": "pro"}, timestamp=happened_at)
        client.capture("user-1", "page_view", {"path": "/billing"})
        client.capture("user-2", "page_view")
        client.flush(timeout=10)

    stored = Event.objects.order_by("id")
    assert [(e.distinct_id, e.event_name) for e in stored] == [
        ("user-1", "signup"),
        ("user-1", "page_view"),
        ("user-2", "page_view"),
    ]
    signup = stored[0]
    assert signup.properties == {"plan": "pro"}
    # The SDK sends sent_at with each batch, so the server corrects for the request's delay;
    # the stored time stays within a few seconds of when the event happened.
    assert abs(signup.timestamp - happened_at) < timedelta(seconds=5)
    assert len({e.uuid for e in stored}) == 3
